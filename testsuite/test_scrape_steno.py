from datetime import date
from path import path
from mpscraper import steno


PAGES_DIR = path(__file__).abspath().parent / 'pages'


def test_2013_06_10(session):
    STENO_URL = 'http://www.cdep.ro/pls/steno/'
    session.url_map.update({
        STENO_URL + 'steno.data?cam=2&idl=1&dat=20130610':
            PAGES_DIR / 'steno.data-20130610',
        STENO_URL + 'steno.stenograma?ids=7277&idm=1&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-1',
        STENO_URL + 'steno.stenograma?ids=7277&idm=2&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-2',
        STENO_URL + 'steno.stenograma?ids=7277&idm=3&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-3',
        STENO_URL + 'steno.stenograma?ids=7277&idm=4&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-4',
        STENO_URL + 'steno.stenograma?ids=7277&idm=5&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-5',
        STENO_URL + 'steno.stenograma?ids=7277&idm=6&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-6',
        STENO_URL + 'steno.stenograma?ids=7277&idm=7&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-7',
        STENO_URL + 'steno.stenograma?ids=7277&idm=8&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-8',
        STENO_URL + 'steno.stenograma?ids=7277&idm=9&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-9',
        STENO_URL + 'steno.stenograma?ids=7277&idm=10&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-10',
        STENO_URL + 'steno.stenograma?ids=7277&idm=11&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-11',
        STENO_URL + 'steno.stenograma?ids=7277&idm=12&idl=1':
            PAGES_DIR / 'steno.stenograma-7277-12',
    })
    steno_scraper = steno.StenogramScraper(session)
    steno_day = steno_scraper.fetch_day(date(2013, 6, 10))
    paragraphs = []
    for steno_section in steno_day.sections:
        for paragraph in steno_section.paragraphs:
            paragraphs.append(paragraph)
    assert len(paragraphs) == 477
    assert paragraphs[0]['speaker_cdep_id'] == 168
    assert paragraphs[0]['text'] == "Stimaţi colegi,"
