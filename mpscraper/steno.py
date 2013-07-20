""" Fetch and parse stenograms """

from datetime import date
from urllib.parse import urlparse, parse_qs
from pyquery import PyQuery as pq
from mpscraper.common import (Scraper, pqitems, fix_encoding,
                              get_cached_session)


class StenoDay:

    def __init__(self):
        self.chapters = []


class StenoChapter:

    def __init__(self):
        self.paragraphs = []


class StenoParagraph(dict):

    pass


class StenogramScraper(Scraper):

    steno_url = 'http://www.cdep.ro/pls/steno/steno.data?cam=2&idl=1'

    def chapters_for_day(self, day):
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
            parent_tr = pq(link_el).parents('tr')[-1]
            headline_el = pq(parent_tr)('td')[-1]
            headline = fix_encoding(pq(headline_el).text())
            yield link, headline

    def get_chapter_serial(self):
        return self.day.strftime('%Y-%m-%d') + '/%02d' % self.chapter_serial

    def next_paragraph_serial(self):
        self.paragraph_serial += 1
        return self.get_chapter_serial() + '-%03d' % self.paragraph_serial

    def trim_name(self, name):
        for prefix in ['Domnul ', 'Doamna ']:
            if name.startswith(prefix):
                return name[len(prefix):]
        else:
            return name

    def parse_steno_page(self, link):
        page = self.fetch_url(link)
        table_rows = pqitems(page, '#pageContent > table tr')
        steno_paragraph = None
        steno_chapter = StenoChapter()
        text_buffer = []

        def save_paragraph():
            text = "\n".join(steno_paragraph.pop('text_buffer'))
            steno_paragraph['text'] = text
            steno_chapter.paragraphs.append(steno_paragraph)

        for tr in table_rows:
            for td in pqitems(tr, 'td'):
                for paragraph in pqitems(td, 'p'):
                    speakers = paragraph('b font[color="#0000FF"]')
                    if speakers:
                        if steno_paragraph:
                            save_paragraph()
                        assert len(speakers) == 1
                        speaker_name = self.trim_name(
                            fix_encoding(speakers.text()))
                        link = speakers.parents('a')
                        if link:
                            qs = parse_qs(urlparse(link.attr('href')).query)
                            assert qs['cam'] == ['2']
                            assert qs['leg'] == ['2012']
                            speaker_cdep_id = int(qs['idm'][0])
                        else:
                            speaker_cdep_id = None
                        steno_paragraph = StenoParagraph({
                            'speaker_cdep_id': speaker_cdep_id,
                            'speaker_name': speaker_name,
                            'text_buffer': [],
                            'serial': self.next_paragraph_serial()
                        })

                    else:
                        if steno_paragraph is None:
                            continue  # still looking for first speaker
                        text = fix_encoding(paragraph.text())
                        steno_paragraph['text_buffer'].append(text)

        if steno_paragraph:
            save_paragraph()

        return steno_chapter

    def fetch_day(self, day):
        self.day = day
        self.chapter_serial = 0
        steno_day = StenoDay()
        steno_day.date = day
        for link, headline in self.chapters_for_day(day):
            self.chapter_serial += 1
            self.paragraph_serial = 0
            steno_chapter = self.parse_steno_page(link)
            steno_chapter.headline = headline
            steno_chapter.serial = self.get_chapter_serial()
            steno_day.chapters.append(steno_chapter)
        return steno_day


if __name__ == '__main__':
    steno_scraper = StenogramScraper(get_cached_session())
    steno_day = steno_scraper.fetch_day(date(2013, 6, 10))
    for steno_chapter in steno_day.chapters:
        for paragraph in steno_chapter.paragraphs:
            print(paragraph)
