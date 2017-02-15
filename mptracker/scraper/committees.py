from pyquery import PyQuery as pq
from mptracker.scraper.common import (
    Scraper, url_args, GenericModel, TableParser, MembershipParser,
)


class Committee(GenericModel):
    pass


class Member(GenericModel):
    pass


class CommitteeMembershipParser(MembershipParser):

    member_cls = Member
    date_fmt = 'eu_dots'
    start_date_txt = "Membru al comisiei din data"
    end_date_txt = "Membru al comisiei până în data"

    role_map = {
        "": "",
        "Preşedinte": "Preşedinte",
        "Vicepreşedinţi": "Vicepreşedinte",
        "Secretari": "Secretar",
        "Membri": "Membru",
        "Membri supleanţi": "Membru supleant",
    }

    def parse_table(self, table_root):
        self.table_parser_args = {}
        if len(table_root.children('tr.rowh')) > 1:
            self.table_parser_args['double_header'] = True
        for member in super().parse_table(table_root):
            if member.mp_ident[1] == 2:  # only deputies, not senators
                member.role = self.role_map[member.role]
                yield member


class CdepCommitteeMembershipParser(CommitteeMembershipParser):

    person_txt = "Deputatul"


class CommonCommitteeMembershipParser(CommitteeMembershipParser):

    person_txt = "Numele şi prenumele"


SENATE_2016_COMMITTEES = [
    (1, "Comisia economică, industrii şi servicii"),
    (3, "Comisia pentru buget, finanţe, activitate bancară şi piaţă de capital"),
    (4, "Comisia pentru agricultură, silvicultură şi dezvoltare rurală"),
    (5, "Comisia pentru politică externă"),
    (6, "Comisia pentru apărare, ordine publică şi siguranţă naţională"),
    (7, "Comisia pentru drepturile omului, culte şi minorităţi"),
    (8, "Comisia pentru muncă, familie şi protecţie socială"),
    (9, "Comisia pentru învăţământ, ştiinţă, tineret şi sport"),
    (10, "Comisia pentru cultură, artă şi mijloace de informare în masă"),
    (11, "Comisia pentru administraţie publică, organizarea teritoriului şi protecţia mediului"),
    (12, "Comisia juridică, de numiri, disciplină, imunităţi şi validări"),
    (14, "Comisia pentru sănătate publică"),
]


class CommitteeScraper(Scraper):

    listing_page_url = \
        'http://www.cdep.ro/pls/parlam/structura.co?cam={chamber_id}&leg=2016'
    committee_url_prefix = \
        'http://www.cdep.ro/pls/parlam/structura.co?'

    def fetch_committees(self):
        for chamber_id in [0, 1, 2]:
            if chamber_id == 1:
                for (id, name) in SENATE_2016_COMMITTEES:
                    yield Committee(
                        cdep_id=id,
                        chamber_id=1,
                        name=name,
                        current_members=[],
                        former_members=[],
                    )
                continue

            url = self.listing_page_url.format(chamber_id=chamber_id)
            listing_page = self.fetch_url(url)

            for row in listing_page.items('table.tip01 tr[valign=top]'):
                cell = row('td').eq(1)
                link = cell('a').eq(0)
                href = link.attr('href')
                assert href.startswith(self.committee_url_prefix)
                args = url_args(href)
                assert args['leg'] == '2016'
                assert args['cam'] == str(chamber_id)
                committee = Committee(
                    cdep_id=int(args['idc']),
                    chamber_id=chamber_id,
                    name=link.text(),
                    current_members=[],
                    former_members=[],
                )
                if chamber_id != 1:
                    self.fetch_committee_members(committee, href, chamber_id)
                yield committee

    def fetch_committee_members(self, committee, committee_url, chamber_id):
        committee_page = self.fetch_url(committee_url)
        mp_tables = list(committee_page.items('table.tip01'))

        if chamber_id == 0:
            membership_parser = CommonCommitteeMembershipParser()
        elif chamber_id == 2:
            membership_parser = CdepCommitteeMembershipParser()

        committee.current_members.extend(
            membership_parser.parse_table(mp_tables[0]))

        if len(mp_tables) > 1:
            committee.former_members.extend(
                membership_parser.parse_table(mp_tables[-1]))
