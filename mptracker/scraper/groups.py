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
        group = Group(current_members=[], former_members=[])

        idg = url_args(group_url).get('idg', type=int)
        if idg == 0:
            # group of unaffiliated MPs
            pass

        else:
            current_title = None
            rows = list(mp_tables[0].items('tr'))
            for row in rows[1:]:
                row_children = row.children()
                next_title = row_children.eq(1).text()
                if next_title:
                    current_title = next_title
                name_link = row_children.eq(2).find('a')

                member = Member(
                    title=current_title,
                    mp_name=name_link.text(),
                    mp_ident=parse_profile_url(name_link.attr('href')),
                    party=row_children.eq(3).text(),
                    start_date=None,
                )

                date_txt = row_children.eq(4).text()
                if date_txt:
                    member.start_date = parse_date(date_txt)

                group.current_members.append(member)

            rows = list(mp_tables[-1].items('tr'))
            has_start = bool("Membru din" in rows[0].text())
            end_date_col = 4 if has_start else 3
            for row in rows[1:]:
                row_children = row.children()
                name_link = row_children.eq(1).find('a')

                member = Member(
                    mp_name=name_link.text(),
                    mp_ident=parse_profile_url(name_link.attr('href')),
                    start_date=None,
                    end_date=parse_date(row_children.eq(end_date_col).text()),
                )

                if has_start:
                    start_txt = row_children.eq(3).text()
                    if start_txt:
                        member.start_date = parse_date(start_txt)

                group.former_members.append(member)

        return group
