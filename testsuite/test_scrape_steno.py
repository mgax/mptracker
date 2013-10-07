from datetime import date
from path import path


PAGES_DIR = path(__file__).abspath().parent / 'pages'


def test_2013_06_10(session):
    from mptracker.scraper.transcripts import TranscriptScraper

    TRANSCRIPT_URL = 'http://www.cdep.ro/pls/steno/'
    session.url_map.update({
        TRANSCRIPT_URL + 'steno.sumar?ids=7277':
            PAGES_DIR / 'steno.sumar-7277',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=1&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-1',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=2&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-2',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=3&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-3',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=4&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-4',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=5&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-5',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=6&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-6',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=7&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-7',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=8&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-8',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=9&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-9',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=10&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-10',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=11&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-11',
        TRANSCRIPT_URL + 'steno.stenograma?ids=7277&idm=12&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-12',
    })
    transcript_scraper = TranscriptScraper(session)
    transcript_session = transcript_scraper.fetch_session(7277)

    assert transcript_session.date == date(2013, 6, 10)

    assert ("cooperarea dintre Parlament şi Guvern în "
            "domeniul afacerilor europene") \
            in transcript_session.chapters[1].headline

    paragraphs = []
    for transcript_chapter in transcript_session.chapters:
        for paragraph in transcript_chapter.paragraphs:
            paragraphs.append(paragraph)
    assert len(paragraphs) == 100
    assert paragraphs[0]['mandate_year'] == 2012
    assert paragraphs[0]['mandate_number'] == 168
    assert "Stimaţi colegi," in paragraphs[0]['text']
    assert "Declar deschise lucrările" in paragraphs[0]['text']

    assert transcript_session.chapters[0].serial == '07277/01'
    chapter_serial_values = [s.serial for s in transcript_session.chapters]
    assert sorted(set(chapter_serial_values)) == chapter_serial_values

    assert paragraphs[0]['serial'] == '07277/01-001'
    paragraph_serial_values = [p['serial'] for p in paragraphs]
    assert sorted(set(paragraph_serial_values)) == paragraph_serial_values
