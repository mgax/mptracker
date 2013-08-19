import re
from pyquery import PyQuery as pq
from mptracker.scraper.common import Scraper, pqitems, get_cdep_id
from mptracker.common import fix_local_chars


class ProposalScraper(Scraper):

    proposals_url = ('http://www.cdep.ro/pls/proiecte/upl_pck.lista'
                     '?cam=2&anp=2013')

    def fix_name(self, name):
        return fix_local_chars(re.sub(r'[\s\-]+', ' ', name))

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
        page = self.fetch_url(url)
        out = {
            'headline': pq('.headline', page).text(),
            'url': url,
        }

        [hook_td] = pqitems(page, ':contains("Nr. înregistrare")')
        metadata_table = pq(hook_td.parents('table')[-1])
        for row in pqitems(metadata_table.children('tr')):
            cols = row.children()
            label = cols.eq(0).text().strip()
            val_td = cols.eq(1) if len(cols) > 1 else None

            if label == "- Camera Deputatilor:":
                out['cdep_serial'] = val_td.text()

            elif label == "Tip initiativa:":
                out['proposal_type'] = val_td.text()

            elif label == "Initiator:":
                sponsors = []
                for a in val_td('a').items():
                    cdep_id = get_cdep_id(a.attr('href'), fail='none')
                    if cdep_id is not None:
                        sponsors.append({
                            'cdep_id': cdep_id,
                            'name': self.fix_name(a.text()),
                        })
                out['sponsors'] = sponsors

        return out
