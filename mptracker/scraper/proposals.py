from pyquery import PyQuery as pq
from mptracker.scraper.common import Scraper, pqitems, get_cdep_id


class ProposalScraper(Scraper):

    proposals_url = ('http://www.cdep.ro/pls/proiecte/upl_pck.lista'
                     '?cam=2&anp=2013')

    def fetch_proposals(self):
        page = self.fetch_url(self.proposals_url)
        the_table = pqitems(page, 'table table table table table')[-1]
        rows = iter(pqitems(the_table, 'tr'))
        assert next(rows).text() == "Numar Titlu Stadiu"
        for row in rows:
            tr_1 = pqitems(row, 'td')[1]
            url = pq('a', tr_1).attr('href')
            assert url.startswith('http://www.cdep.ro/pls/proiecte'
                                  '/upl_pck.proiect?cam=2&idp=')
            yield self.fetch_proposal_details(url)

    def fetch_proposal_details(self, url):
        return url
