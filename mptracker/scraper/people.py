from urllib.parse import urlparse, parse_qs
from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, pqitems, get_cached_session,
                                      get_cdep_id)


class PersonScraper(Scraper):

    people_url = 'http://www.cdep.ro/pls/parlam/structura.de?leg={year}'

    def fetch_people(self, year=2012):
        people_page = self.fetch_url(self.people_url.format(year=year))
        for tr in pqitems(people_page, 'tr'):
            for a in pqitems(tr, 'a'):
                href = a.attr('href')
                if 'structura.mp' in href:
                    name = a.text()
                    cdep_id = get_cdep_id(href)
                    td = a.parents('tr')[2]
                    county_name = pq(td[3]).text()
                    minority = False
                    if county_name in ["Mino.", "Minoritati"]:
                        county_name = None
                        minority = True

                    yield {
                        'cdep_id': cdep_id,
                        'name': name,
                        'county_name': county_name,
                        'minority': minority,
                    }


if __name__ == '__main__':
    person_scraper = PersonScraper(get_cached_session())
    print(list(person_scraper.fetch_people()))
