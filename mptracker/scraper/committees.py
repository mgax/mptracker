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


class CommitteeScraper(Scraper):

    listing_page_url = \
        'http://www.cdep.ro/pls/parlam/structura.co?cam={chamber_id}&leg=2016'
    committee_url_prefix = \
        'http://www.cdep.ro/pls/parlam/structura.co?'

    def fetch_committees(self):
        for chamber_id in [0, 1, 2]:
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
