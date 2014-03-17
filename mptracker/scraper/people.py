from pyquery import PyQuery as pq
from mptracker.common import fix_local_chars
from mptracker.scraper.common import (Scraper, GenericModel, parse_profile_url,
                                      parse_date)


class Mandate(GenericModel):
    pass


def match_split_name(last_first, first_last_upper):
    bits = first_last_upper.split()
    first_name = ' '.join(b for b in bits if not b.isupper())
    last_name = ' '.join(b.title() for b in bits if b.isupper())
    assert last_first == "%s %s" % (last_name, first_name)
    return (first_name, last_name)


class MandateScraper(Scraper):

    mandates_url = 'http://www.cdep.ro/pls/parlam/structura.de?leg={year}'

    def parse_mandates(self, table, ended=False):
        row_list = list(table.children().items())
        uninominal = bool('Colegiul uninominal' in row_list[1].text())
        if uninominal:
            college_col = 4
            party_col = 5
        else:
            college_col = None
            party_col = 4

        has_start_date = bool('Membru din' in row_list[0].text())

        for row in row_list[2:]:
            cols = row.children()
            link = cols.eq(1).find('a')
            (year, chamber, number) = parse_profile_url(link.attr('href'))

            last_first = link.text()
            person_page = self.fetch_url(link.attr('href'))
            picture = person_page.find('a.highslide')
            first_last = (
                person_page.find('.headline').html()
                .split('<br/>')[0]
                .split(',')[0]
                .split('\xa0\xa0\xa0\xa0')[0]
            )
            (first_name, last_name) = match_split_name(last_first, first_last)

            mandate = Mandate(
                year=year,
                chamber_number=chamber,
                cdep_number=number,
                person_name=last_first,
                person_first_name=first_name,
                person_last_name=last_name,
                minority=False,
                end_date=None,
                picture_url=picture.attr('href'),
            )

            if (cols.eq(2).text() in ["ales la nivel naţional", ""] and
                cols.eq(3).text() in ["Mino.", "Minoritati", u"Minorităţi"]):
                mandate.minority = True

            else:
                mandate.constituency = int(cols.eq(2).text())
                if college_col:
                    mandate.college = int(cols.eq(college_col).text())
                else:
                    mandate.college = None
                mandate.party_name = cols.eq(party_col).text()

                county_name = fix_local_chars(cols.eq(3).text().title())
                if county_name == "Bistrița-Năsăud":
                    county_name = "Bistrița Năsăud"
                mandate.county_name = county_name

            if ended:
                end_date_col = 6
                if mandate.minority:
                    end_date_col -= 1
                if not has_start_date:
                    end_date_col -= 1
                if uninominal and not mandate.minority:
                    end_date_col += 1
                mandate.end_date = parse_date(
                    cols.eq(end_date_col).text(),
                    fmt='ro_short_month',
                )

            yield mandate

    def fetch(self, year=2012):
        mandates_page = self.fetch_url(self.mandates_url.format(year=year))
        headline_current = mandates_page.find('td.headline')
        parent_td = headline_current.parents('td').eq(-2)
        parent_table = (
            parent_td
                .children('table').eq(1)
                .children('tr').eq(0)
                .children('td').eq(1)
                .children('table').eq(2)
        )
        data_tables = parent_table.children('td').eq(0).children('table')

        return (
            list(self.parse_mandates(data_tables.eq(0))) +
            list(self.parse_mandates(data_tables.eq(1), ended=True))
        )
