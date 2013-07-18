""" Fetch and parse stenograms """

from datetime import date
from urlparse import urlparse, parse_qs
from path import path
from pyquery import PyQuery as pq


class StenogramScraper(object):

    def fetch_url(self, *args, **kwargs):
        return pq(*args, **kwargs)

    def links_for_day(self, day):
        contents = self.fetch_url('http://www.cdep.ro/pls/steno/steno.data',
                                  {'cam': 2, 'idl': 1,
                                   'dat': day.strftime('%Y%m%d')})
        for link_el in contents('td.headlinetext1 b a'):
            link = link_el.attrib['href']
            plink = urlparse(link)
            assert plink.path == '/pls/steno/steno.stenograma'
            if ',' in parse_qs(plink.query)['idm'][0]:
                # this is a fragment page. we can ignore it since we
                # already have the content from the parent page.
                continue
            yield link

    def fetch_day(self, day):
        for link in self.links_for_day(day):
            print link


if __name__ == '__main__':
    import requests_cache
    here = path(__file__).abspath().parent
    requests_cache.install_cache(here / 'http_cache')
    StenogramScraper().fetch_day(date(2013, 6, 10))
