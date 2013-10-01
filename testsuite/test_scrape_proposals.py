from path import path

PAGES_DIR = path(__file__).abspath().parent / 'pages'


def test_thing(session):
    from mptracker.scraper.proposals import ProposalScraper

    listing_url = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                            'idm=%d&leg=%d&cam=2&pag=2&idl=1&prn=0&par=')
    proposal_url = ('http://www.cdep.ro/pls/proiecte/upl_pck.proiect?')
    session.url_map.update({
        listing_url % (126, 2012): PAGES_DIR / 'proposal-listing-2012-126',
        proposal_url + 'idp=17135&cam=1': PAGES_DIR / 'proposal-1-17135',
        proposal_url + 'cam=2&idp=13348': PAGES_DIR / 'proposal-2-13348',
        proposal_url + 'idp=17422&cam=1': PAGES_DIR / 'proposal-1-17422',
    })

    scraper = ProposalScraper(session)
    proposals = scraper.fetch_from_mp_pages([(2012, 126)])

    assert len(proposals) == 3
    proposals.sort(key=lambda p: p['title'])
    pr = proposals[0]
    assert pr['_sponsorships'] == [(2012, 126)]
    assert pr['cdep_serial'] == 'BP346/04.06.2013'
    assert pr['combined_id'] == 'cdep=BP346/2013 senate=L430/2013'
    assert pr['decision_chamber'] == 'cdep'
    assert pr['proposal_type'] == 'Propunere legislativa'
    assert pr['pdf_url'] == ('http://www.cdep.ro/proiecte/bp/'
                             '2013/300/40/6/pl346.pdf')
    assert "declararea zilei de 10 mai" in pr['title']
    assert pr['url'] == ('http://www.cdep.ro/pls/proiecte/upl_pck.proiect'
                         '?cam=2&idp=13348')
