""" Fetch and parse stenograms """

from datetime import date
from urllib.parse import urlparse, parse_qs
from mpscraper.common import (Scraper, pqitems, fix_encoding,
                              install_requests_cache)


class StenogramScraper(Scraper):

    steno_url = 'http://www.cdep.ro/pls/steno/steno.data?cam=2&idl=1'

    def links_for_day(self, day):
        contents = self.fetch_url(self.steno_url,
                                  {'dat': day.strftime('%Y%m%d')})
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
                    speakers = paragraph('b a[target="PARLAMENTARI"]')
                    if speakers:
                        assert len(speakers) == 1
                        speaker_name = fix_encoding(speakers.text())
                        qs = parse_qs(urlparse(speakers.attr('href')).query)
                        assert qs['cam'] == ['2']
                        assert qs['leg'] == ['2012']
                        speaker_cdep_id = int(qs['idm'][0])
                        speaker = (speaker_cdep_id, speaker_name)

                    else:
                        if speaker is None:
                            continue  # still looking for first speaker
                        (speaker_cdep_id, speaker_name) = speaker
                        text = fix_encoding(paragraph.text())
                        yield {
                            'speaker_cdep_id': speaker_cdep_id,
                            'speaker_name': speaker_name,
                            'text': text,
                        }

    def fetch_day(self, day):
        for link in self.links_for_day(day):
            for paragraph in self.parse_steno_page(link):
                yield paragraph


if __name__ == '__main__':
    install_requests_cache()
    for paragraph in StenogramScraper().fetch_day(date(2013, 6, 10)):
        print(paragraph)
