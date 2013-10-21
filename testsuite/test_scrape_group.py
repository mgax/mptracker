from datetime import date
from path import path

PAGES_DIR = path(__file__).abspath().parent / 'pages'
STRUCTURE_URL = 'http://www.cdep.ro/pls/parlam/structura.gp'


def test_simple_scraping(session):
    from mptracker.scraper.groups import GroupScraper

    session.url_map.update({
        STRUCTURE_URL: PAGES_DIR / 'structura-index-modified',
        STRUCTURE_URL + '?idg=0': PAGES_DIR / 'structura-group0',
        STRUCTURE_URL + '?idg=1': PAGES_DIR / 'structura-group1',
    })

    scraper = GroupScraper(session)
    groups = list(scraper.fetch())

    psd = groups[1]
    assert len(psd.current_members) == 165
    assert len(psd.former_members) == 2

    current_3 = psd.current_members[3]
    assert current_3.mp_name == "Itu Cornel"
    assert current_3.party == 'PSD'
    assert current_3.start_date is None
    assert current_3.title == 'Vicelideri'

    current_14 = psd.current_members[14]
    assert current_14.start_date == date(2013, 9, 2)

    current_84 = psd.current_members[84]
    assert current_84.start_date == date(2013, 9, 18)

    former_0 = psd.former_members[0]
    assert former_0.mp_name == "Cernea Remus-Florinel"
