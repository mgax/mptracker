""" Fetch and parse transcripts """

from datetime import date
from urllib.parse import urlparse, parse_qs
from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, pqitems, get_cached_session,
                                      parse_cdep_id)


class Day:

    def __init__(self):
        self.chapters = []


class Chapter:

    def __init__(self):
        self.paragraphs = []


class Paragraph(dict):

    pass


class TranscriptScraper(Scraper):

    transcript_url = 'http://www.cdep.ro/pls/steno/steno.data?cam=2&idl=1'

    def chapters_for_day(self, day):
        contents = self.fetch_url(self.transcript_url,
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
            headline = pq(headline_el).text()
            yield link, headline

    def get_chapter_serial(self):
        return self.day.strftime('%Y-%m-%d') + '/%02d' % self.chapter_serial

    def next_paragraph_serial(self):
        self.paragraph_serial += 1
        return self.get_chapter_serial() + '-%03d' % self.paragraph_serial

    def trim_name(self, name):
        for prefix in ['Domnul ', 'Doamna ', 'Domnişoara ']:
            if name.startswith(prefix):
                return name[len(prefix):]
        else:
            return name

    def parse_transcript_page(self, link):
        page = self.fetch_url(link)
        table_rows = pqitems(page, '#pageContent > table tr')
        transcript_paragraph = None
        transcript_chapter = Chapter()

        def save_paragraph():
            text = "\n".join(transcript_paragraph.pop('text_buffer'))
            transcript_paragraph['text'] = text
            transcript_chapter.paragraphs.append(transcript_paragraph)

        for tr in table_rows:
            for td in pqitems(tr, 'td'):
                for paragraph in pqitems(td, 'p'):
                    speakers = paragraph('b font[color="#0000FF"]')
                    if speakers:
                        if transcript_paragraph:
                            save_paragraph()
                        assert len(speakers) == 1
                        speaker_name = self.trim_name(speakers.text())
                        link = speakers.parents('a')
                        if not link:
                            transcript_paragraph = None
                            continue
                        (year, number) = parse_cdep_id(link.attr('href'))
                        transcript_paragraph = Paragraph({
                            'mandate_year': year,
                            'mandate_number': number,
                            'speaker_name': speaker_name,
                            'text_buffer': [],
                            'serial': self.next_paragraph_serial()
                        })

                    else:
                        if transcript_paragraph is None:
                            continue
                        text = paragraph.text()
                        transcript_paragraph['text_buffer'].append(text)

        if transcript_paragraph:
            save_paragraph()

        return transcript_chapter

    def fetch_day(self, day):
        self.day = day
        self.chapter_serial = 0
        transcript_day = Day()
        transcript_day.date = day
        for link, headline in self.chapters_for_day(day):
            self.chapter_serial += 1
            self.paragraph_serial = 0
            transcript_chapter = self.parse_transcript_page(link)
            transcript_chapter.headline = headline
            transcript_chapter.serial = self.get_chapter_serial()
            transcript_day.chapters.append(transcript_chapter)
        return transcript_day


if __name__ == '__main__':
    transcript_scraper = TranscriptScraper(get_cached_session())
    transcript_day = transcript_scraper.fetch_day(date(2013, 6, 10))
    for transcript_chapter in transcript_day.chapters:
        for paragraph in transcript_chapter.paragraphs:
            print(paragraph)
