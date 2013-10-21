from pyquery import PyQuery as pq
from mptracker.common import fix_local_chars
from mptracker.scraper.common import (Scraper, GenericModel, parse_cdep_id,
                                      parse_date)


class Mandate(GenericModel):
    pass


class MandateScraper(Scraper):

    mandates_url = 'http://www.cdep.ro/pls/parlam/structura.de?leg={year}'

    def parse_mandates(self, table, ended=False):
        for row in list(table.children().items())[2:]:
            cols = row.children()
            link = cols.eq(1).find('a')
            (mandate_year, cdep_number) = parse_cdep_id(link.attr('href'))

            mandate = Mandate(
                year=mandate_year,
                cdep_number=cdep_number,
                person_name=link.text(),
                minority=False,
                end_date=None
            )

            if cols.eq(2).text() == "ales la nivel naţional":
                mandate.minority = True

            else:
                mandate.constituency = int(cols.eq(2).text())
                mandate.college = int(cols.eq(4).text())
                mandate.party_name = cols.eq(5).text()

                county_name = fix_local_chars(cols.eq(3).text().title())
                if county_name == "Bistrița-Năsăud":
                    county_name = "Bistrița Năsăud"
                mandate.county_name = county_name

            if ended:
                mandate.end_date = parse_date(cols.eq(6).text())

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
