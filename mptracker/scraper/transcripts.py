""" Fetch and parse transcripts """

from datetime import datetime
from urllib.parse import urlparse, parse_qs
from pyquery import PyQuery as pq
import yaml
from mptracker.scraper.common import (Scraper, pqitems, get_cached_session,
                                      parse_profile_url, open_scraper_resource)


class Session:

    def __init__(self):
        self.chapters = []


class Chapter:

    def __init__(self):
        self.paragraphs = []


class Paragraph(dict):

    pass


class TranscriptScraper(Scraper):

    session_url = 'http://www.cdep.ro/pls/steno/steno.sumar?ids=%d'

    transcript_url = ('http://www.cdep.ro/pls/steno/steno.data'
                      '?cam=2&idl=1&dat=%s')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open_scraper_resource('transcript_exceptions.yaml') as f:
            self.exceptions = yaml.load(f)

    def get_session_date(self, page):
        td = page.find(':contains("Sunteţi în secţiunea")')
        date_str = td.parent().text().split()[-1]
        return datetime.strptime(date_str, '%d-%m-%Y').date()

    def chapters_for_session(self, page):
        for link_el in page('td.headlinetext1 b a'):
            link = link_el.attrib['href']
            plink = urlparse(link)
            assert plink.path == '/pls/steno/steno.stenograma', \
                    "%s -> %s" % (self.cdeppk, link)
            if ',' in parse_qs(plink.query)['idm'][0]:
                # this is a fragment page. we can ignore it since we
                # already have the content from the parent page.
                continue
            parent_tr = pq(link_el).parents('tr')[-1]
            headline_el = pq(parent_tr)('td')[-1]
            headline = pq(headline_el).text()
            yield link, headline

    def get_chapter_serial(self):
        return '%05d/%02d' % (self.session_cdeppk, self.chapter_serial)

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
                        serial = self.next_paragraph_serial()
                        assert len(speakers) == 1
                        speaker_name = self.exceptions['names'].get(serial)
                        if not speaker_name:
                            speaker_name = self.trim_name(speakers.text())
                        link = speakers.parents('a')
                        if not link:
                            transcript_paragraph = None
                            continue
                        (year, chamber, number) = \
                            parse_profile_url(link.attr('href'))
                        transcript_paragraph = Paragraph({
                            'mandate_year': year,
                            'mandate_chamber': chamber,
                            'mandate_number': number,
                            'speaker_name': speaker_name,
                            'text_buffer': [],
                            'serial': serial,
                        })

                    else:
                        if transcript_paragraph is None:
                            continue
                        text = paragraph.text()
                        transcript_paragraph['text_buffer'].append(text)

        if transcript_paragraph:
            save_paragraph()

        return transcript_chapter

    def fetch_session(self, cdeppk):
        self.session_cdeppk = cdeppk
        self.chapter_serial = 0
        transcript_session = Session()
        session_page = self.fetch_url(self.session_url % self.session_cdeppk)
        transcript_session.date = self.get_session_date(session_page)
        for link, headline in self.chapters_for_session(session_page):
            self.chapter_serial += 1
            self.paragraph_serial = 0
            transcript_chapter = self.parse_transcript_page(link)
            transcript_chapter.headline = headline
            transcript_chapter.serial = self.get_chapter_serial()
            transcript_session.chapters.append(transcript_chapter)
        return transcript_session
