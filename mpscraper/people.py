from urllib.parse import urlparse, parse_qs
from mpscraper.common import Scraper, pqitems, get_cached_session


class PersonScraper(Scraper):

    people_url = 'http://www.cdep.ro/pls/parlam/structura.de?leg=2012'

    def fetch_people(self):
        people_page = self.fetch_url(self.people_url)
        for tr in pqitems(people_page, 'tr'):
            for a in pqitems(tr, 'a'):
                href = a.attr('href')
                if 'structura.mp' in href:
                    name = a.text()
                    cdep_id = int(parse_qs(urlparse(href).query)['idm'][0])
                    yield {
                        'cdep_id': cdep_id,
                        'name': name,
                    }


if __name__ == '__main__':
    person_scraper = PersonScraper(get_cached_session())
    print(list(person_scraper.fetch_people()))
