from datetime import date
import re
from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url)


class Group(GenericModel):
    pass


class Member(GenericModel):
    pass


MONTHS = {'ian': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mai': 5, 'iun': 6,
          'iul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}


def parse_date(txt):
    m = re.match(r'^(?P<day>\d{1,2}) (?P<month>\w+)\.? (?P<year>\d{4})$', txt)
    assert m is not None, "can't parse date: %r" % txt
    return date(
        int(m.group('year')),
        MONTHS[m.group('month')],
        int(m.group('day')),
    )


class GroupScraper(Scraper):

    index_url = 'http://www.cdep.ro/pls/parlam/structura.gp'

    def fetch(self):
        index_page = self.fetch_url(self.index_url)
        headline = index_page.find('td.headline')
        parent_table = pq(headline.parents('table')[-2])
        table = list(parent_table.items('table'))[-1]

        url_set = set()
        for link in table.items('tr > td > b > a'):
            url_set.add(link.attr('href'))

        for url in sorted(url_set):
            yield self.fetch_group(url)

    def fetch_group(self, group_url):
        group_page = self.fetch_url(group_url)
        headline = group_page.find('td.headline')
        parent_td = pq(headline.parents('td')[-1])
        mp_tables = list(parent_td.items('table table'))
        short_name = group_page.find('.cale2').text().split('>')[-1].strip()

        group = Group(
            is_independent=False,
            current_members=[],
            former_members=[],
            name=headline.text(),
            short_name=short_name,
        )

        idg = url_args(group_url).get('idg', type=int)
        if idg == 0:
            # group of unaffiliated MPs
            group.is_independent = True
            group.current_members.extend(
                self.fetch_current_independent_members(mp_tables[0]))

        else:
            group.current_members.extend(
                self.fetch_current_members(mp_tables[0]))

            if len(mp_tables) > 1:
                group.former_members.extend(
                    self.fetch_former_members(mp_tables[-1]))

        return group

    def fetch_current_independent_members(self, table):
        rows = list(table.items('tr'))
        cols = {k: n for n, k in enumerate(self.parse_cols(rows[0]))}
        for row in rows[1:]:
            row_children = row.children()
            name_link = row_children.eq(cols['person']).find('a')

            member = Member(
                mp_name=name_link.text(),
                mp_ident=parse_profile_url(name_link.attr('href')),
                start_date=None,
                end_date=None,
            )

            yield member

    def parse_cols(self, row):
        names = {
            "Funcţia": 'title',
            "Nume şi prenume": 'person',
            "Membru din": 'start_date',
            "Membru până": 'end_date',
        }
        for col in row.items('td'):
            yield names.get(col.text(), '??')

    def fetch_current_members(self, table):
        current_title = None
        rows = list(table.items('tr'))
        cols = {k: n for n, k in enumerate(self.parse_cols(rows[0]))}
        for row in rows[1:]:
            row_children = row.children()
            next_title = row_children.eq(cols['title']).text()
            if next_title:
                current_title = next_title
            name_link = row_children.eq(cols['person']).find('a')

            member = Member(
                title=current_title,
                mp_name=name_link.text(),
                mp_ident=parse_profile_url(name_link.attr('href')),
                start_date=None,
                end_date=None,
            )

            if 'start_date' in cols:
                date_txt = row_children.eq(cols['start_date']).text()
                if date_txt:
                    member.start_date = parse_date(date_txt)

            yield member

    def fetch_former_members(self, table):
        rows = list(table.items('tr'))
        cols = {k: n for n, k in enumerate(self.parse_cols(rows[0]))}
        for row in rows[1:]:
            row_children = row.children()
            name_link = row_children.eq(cols['person']).find('a')

            member = Member(
                mp_name=name_link.text(),
                mp_ident=parse_profile_url(name_link.attr('href')),
                start_date=None,
                end_date=parse_date(row_children.eq(cols['end_date']).text()),
            )

            if 'start_date' in cols:
                start_txt = row_children.eq(cols['start_date']).text()
                if start_txt:
                    member.start_date = parse_date(start_txt)

            yield member
