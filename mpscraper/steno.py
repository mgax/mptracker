""" Fetch and parse stenograms """

from datetime import date
from urlparse import urlparse, parse_qs
from path import path
from pyquery import PyQuery as pq


def fix_encoding(text):
    return text.encode('latin-1').decode('iso-8859-2')


def pqitems(ob, selector=None):
    cls = type(ob)
    if selector is None:
        found = ob
    else:
        found = ob(selector)
    return (cls(el) for el in found)


class StenogramScraper(object):

    def fetch_url(self, *args, **kwargs):
        page = pq(*args, parser='html', **kwargs)
        page.make_links_absolute()
        return page

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

    def parse_steno_page(self, link):
        page = self.fetch_url(link)
        table_rows = pqitems(page, '#pageContent > table tr')
        speaker = None
        for tr in table_rows:
            for td in pqitems(tr, 'td'):
                for paragraph in pqitems(td, 'p'):
                    speakers = paragraph('b a[target="PARLAMENTARI"] font')
                    if speakers:
                        [speaker_el] = speakers
                        speaker = fix_encoding(pq(speaker_el).text())

                    else:
                        if speaker is None:
                            continue  # still looking for first speaker
                        text = fix_encoding(paragraph.text())
                        yield {
                            'speaker': speaker,
                            'text': text,
                        }

    def fetch_day(self, day):
        for link in self.links_for_day(day):
            for paragraph in self.parse_steno_page(link):
                print paragraph


if __name__ == '__main__':
    import requests_cache
    here = path(__file__).abspath().parent
    requests_cache.install_cache(here / 'http_cache')
    StenogramScraper().fetch_day(date(2013, 6, 10))
