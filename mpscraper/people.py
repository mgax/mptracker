from urllib.parse import urlparse, parse_qs
from mpscraper.common import (Scraper, pqitems, fix_encoding,
                              install_requests_cache)


class PersonScraper(Scraper):

    people_url = 'http://www.cdep.ro/pls/parlam/structura.de?leg=2012'

    def fetch_people(self):
        people_page = self.fetch_url(self.people_url)
        for tr in pqitems(people_page, 'tr'):
            for a in pqitems(tr, 'a'):
                href = a.attr('href')
                if 'structura.mp' in href:
                    name = fix_encoding(a.text())
                    id_cdep = int(parse_qs(urlparse(href).query)['idm'][0])
                    yield {
                        'id_cdep': id_cdep,
                        'name': name,
                    }


if __name__ == '__main__':
    install_requests_cache()
    print(list(PersonScraper().fetch_people()))
