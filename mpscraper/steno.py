""" Fetch and parse stenograms """

from datetime import date
from urlparse import urlparse, parse_qs
from path import path
from pyquery import PyQuery as pq


def fetch_day(day):
    contents = pq('http://www.cdep.ro/pls/steno/steno.data',
                  {'cam': 2, 'dat': day.strftime('%Y%m%d'), 'idl': 1})
    for link_el in contents('td.headlinetext1 b a'):
        link = link_el.attrib['href']
        plink = urlparse(link)
        assert plink.path == '/pls/steno/steno.stenograma'
        if ',' in parse_qs(plink.query)['idm'][0]:
            # this is a fragment page. we can ignore it since we
            # already have the content from the parent page.
            continue
        print link


if __name__ == '__main__':
    import requests_cache
    here = path(__file__).abspath().parent
    requests_cache.install_cache(here / 'http_cache')
    fetch_day(date(2013, 6, 10))
