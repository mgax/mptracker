from collections import namedtuple
from pyquery import PyQuery as pq
from mptracker.scraper.common import (
    Scraper, url_args, GenericModel, MembershipParser,
)


Interval = namedtuple('Interval', ['start', 'end', 'group'])


class Group(GenericModel):

    def __repr__(self):
        return "<Group {s.short_name}>".format(s=self)


class Member(GenericModel):

    def get_interval(self):
        return Interval(self.start_date, self.end_date, self.group)


class GroupMembershipParser(MembershipParser):

    member_cls = Member


class GroupScraper(Scraper):

    index_url = 'http://www.cdep.ro/pls/parlam/structura.gp?leg={}'

    def fetch(self, year):
        index_page = self.fetch_url(self.index_url.format(year))
        headline = index_page.find('td.headline')
        parent_table = pq(headline.parents('table')[-2])
        table = list(parent_table.items('table'))[-1]

        url_set = set()
        for link in table.items('tr > td > b > a'):
            url_set.add(link.attr('href'))

        group_list = [self.fetch_group(url, year) for url in sorted(url_set)]
        group_list.sort(key=lambda g: g.idg)
        return group_list

    def fetch_group(self, group_url, year):
        group_page = self.fetch_url(group_url)
        headline = group_page.find('td.headline')
        parent_td = pq(headline.parents('td')[-1])
        mp_tables = list(parent_td.items('table table'))
        short_name = group_page.find('.cale2').text().split('>')[-1].strip()

        group = Group(
            idg=url_args(group_url).get('idg', type=int),
            is_independent=False,
            current_members=[],
            former_members=[],
            name=headline.text(),
            short_name=short_name,
            year=year,
        )

        membership_parser = GroupMembershipParser()

        if group.idg == 0:
            # group of unaffiliated MPs
            group.is_independent = True
            group.short_name = "Indep."

        group.current_members.extend(
            membership_parser.parse_table(mp_tables[0]))

        if len(mp_tables) > 1:
            group.former_members.extend(
                membership_parser.parse_table(mp_tables[-1]))

        for member in group.current_members + group.former_members:
            member.group = group

        for member in group.current_members + group.former_members:
            if year == 2000 and member.mp_ident.number == 170:
                member.mp_name = "Mălaimare Mihai"

            if year == 2004 and member.mp_ident.number == 58:
                    member.mp_name = "Chiper Constantin Cătălin"

            if year == 2004 and member.mp_ident.number == 88:
                member.mp_name = "Mălaimare Mihai"

            if year == 2004 and member.mp_ident.number == 329:
                member.mp_name = "Bónis István"

        return group
