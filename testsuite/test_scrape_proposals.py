from datetime import date
from path import path
import pytest

PAGES_DIR = path(__file__).abspath().parent / 'pages'
LISTING_URL = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                        'idm=%d&leg=%d&cam=2&pag=2&idl=1&prn=0&par=')
PROPOSAL_URL = ('http://www.cdep.ro/pls/proiecte/upl_pck.proiect?')


def test_simple_scraping(session):
    from mptracker.scraper.proposals import ProposalScraper

    session.url_map.update({
        LISTING_URL % (126, 2012): PAGES_DIR / 'proposal-listing-2012-126',
        PROPOSAL_URL + 'idp=17135&cam=1': PAGES_DIR / 'proposal-1-17135',
        PROPOSAL_URL + 'idp=13348&cam=2': PAGES_DIR / 'proposal-2-13348',
        PROPOSAL_URL + 'idp=17422&cam=1': PAGES_DIR / 'proposal-1-17422',
        PROPOSAL_URL + 'idp=17343&cam=1': PAGES_DIR / 'proposal-1-17343',
    })

    scraper = ProposalScraper(session)
    proposals = scraper.fetch_from_mp_pages([(2012, 126)])

    assert len(proposals) == 3
    proposals.sort(key=lambda p: p.title)
    pr = proposals[0]
    assert pr.sponsorships == [(2012, 126)]
    assert pr.number_bpi == '346/04-06-2013'
    assert pr.number_cdep == 'BP346/04.06.2013'
    assert pr.number_senate == 'L430/03.09.2013'
    assert pr.decision_chamber == 'cdep'
    assert pr.proposal_type == 'Propunere legislativa'
    assert pr.pdf_url == ('http://www.cdep.ro/proiecte/bp/'
                          '2013/300/40/6/pl346.pdf')
    assert "declararea zilei de 10 mai" in pr.title
    assert pr.url == ('http://www.cdep.ro/pls/proiecte/upl_pck.proiect'
                      '?idp=13348&cam=2')


def test_correlate_cdep_senate(session):
    from mptracker.scraper.proposals import ProposalScraper

    session.url_map.update({
        LISTING_URL % (65, 2012): PAGES_DIR / 'proposal-listing-2012-65',
        PROPOSAL_URL + 'idp=17113&cam=1': PAGES_DIR / 'proposal-1-17113',
        PROPOSAL_URL + 'idp=13330&cam=2': PAGES_DIR / 'proposal-2-13330',
        PROPOSAL_URL + 'idp=13526&cam=2': PAGES_DIR / 'proposal-2-13526',
        PROPOSAL_URL + 'idp=17422&cam=1': PAGES_DIR / 'proposal-1-17422',
        PROPOSAL_URL + 'idp=17334&cam=1': PAGES_DIR / 'proposal-1-17334',
    })

    scraper = ProposalScraper(session)
    proposals = scraper.fetch_from_mp_pages([(2012, 65)])

    assert len(proposals) == 4
    proposals.sort(key=lambda p: p.title)
    pr = proposals[0]
    assert pr.title == ('BP327/2013 Propunere legislativă privind '
                        'facilitățile acordate șomerilor pentru '
                        'transportul intern')
    assert pr.cdeppk_cdep == 13330
    assert pr.cdeppk_senate == 17334


def test_get_activity(session):
    from mptracker.scraper.proposals import ProposalScraper
    PROP_URL = 'http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=13037'

    session.url_map.update({
        PROP_URL: PAGES_DIR / 'proposal-2-13037',
    })

    scraper = ProposalScraper(session)
    page = scraper.fetch_url(PROP_URL)
    activity = scraper.get_activity(page)
    assert "prezentare în Biroul Permanent" in activity[0].html
    assert activity[0].location == 'CD'
    assert activity[0].date == date(2013, 2, 11)
    assert activity[3].date == date(2013, 6, 5)
    assert "la Camera Deputaţilor pentru dezbatere" in activity[3].html
    assert "trimis pentru aviz la" in activity[3].html
    assert activity[4].date == date(2013, 6, 13)
    assert activity[-1].date == date(2013, 6, 25)
    assert "primire aviz de la" in activity[-1].html
    assert "Comisia pentru sănătate şi familie" in activity[-1].html
    assert '(pdf)' in activity[-1].html


def test_merge_activity(session):
    from mptracker.scraper.proposals import ProposalScraper
    PROP_URL_CDEP = PROPOSAL_URL + 'idp=13037&cam=2'
    PROP_URL_SENATE = PROPOSAL_URL + 'idp=17003&cam=1'

    session.url_map.update({
        PROP_URL_CDEP: PAGES_DIR / 'proposal-2-13037',
        PROP_URL_SENATE: PAGES_DIR / 'proposal-1-17003',
    })

    scraper = ProposalScraper(session)
    activity = scraper.merge_activity(
        scraper.get_activity(scraper.fetch_url(PROP_URL_CDEP)),
        scraper.get_activity(scraper.fetch_url(PROP_URL_SENATE)))
    assert activity[3].date == date(2013, 2, 12)
    assert "înregistrat la Senat pentru dezbatere" in activity[3].html
    assert "cu nr.b38 (adresa nr.bpi19/11-02-2013)" in activity[3].html
    assert activity[4].date == date(2013, 2, 19)
    assert "trimis pentru aviz la Consiliul legislativ" in activity[4].html


@pytest.mark.parametrize(['in_html', 'out_html'], [
    ('', ''),
    ('  ', ''),
    ('&', '<p>&amp;</p>'),
    ('<<', ''),
    ('<script>foo</script>', '<div/>'),
    ('foo', '<p>foo</p>'),
    ('<div><p>bar</p></div>', '<div><p>bar</p></div>'),
    ('șțăîâüø£€™æ…‘“', '<p>șțăîâüø£€™æ…‘“</p>'),
])
def test_sanitize(in_html, out_html):
    from mptracker.scraper.common import sanitize
    assert sanitize(in_html) == out_html
