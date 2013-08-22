import re
import logging
from pyquery import PyQuery as pq
from mptracker.scraper.common import Scraper, pqitems, get_cdep_id
from mptracker.common import fix_local_chars


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ProposalScraper(Scraper):

    proposal_listings = [
        'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam=2&anp=2013',
        'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam=2&anb=2013',
        'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam=1&anp=2013',
        'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam=1&anb=2013',
    ]

    def fix_name(self, name):
        return fix_local_chars(re.sub(r'[\s\-]+', ' ', name))

    def fetch_all_proposals(self):
        for listing_url in self.proposal_listings:
            yield from self.fetch_proposals(listing_url)

    def fetch_proposals(self, listing_url):
        page = self.fetch_url(listing_url)
        the_table = pqitems(page, 'table table table table table')[-1]
        rows = iter(pqitems(the_table, 'tr'))
        assert next(rows).text() == "Numar Titlu Stadiu"
        for row in rows:
            tr_1 = pqitems(row, 'td')[1]
            url = pq('a', tr_1).attr('href')
            assert url.startswith('http://www.cdep.ro/pls/proiecte'
                                  '/upl_pck.proiect?'), url
            yield self.fetch_proposal_details(url)

    def fetch_proposal_details(self, url):
        page = self.fetch_url(url)
        out = {
            'title': pq('.headline', page).text(),
            'url': url,
        }
        if '?cam=2&' in url:
            out['from_cdep_listing'] = True
        else:
            assert '?cam=1&' in url
            out['from_cdep_listing'] = False

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
                cdep_sponsors = []
                for a in val_td('a').items():
                    cdep_id = get_cdep_id(a.attr('href'), fail='none')
                    if cdep_id is not None:
                        cdep_sponsors.append({
                            'cdep_id': cdep_id,
                            'name': self.fix_name(a.text()),
                        })

                if len(cdep_sponsors) > 0:
                    out['cdep_sponsors'] = cdep_sponsors
                    out['sponsored_by'] = 'cdep'

                elif val_td.text() == "Guvern":
                    out['sponsored_by'] = 'govt'

                elif 'senator' in val_td.text():
                    out['sponsored_by'] = 'senate'

                else:
                    raise RuntimeError("Can't parse sponsorship: %r"
                                       % val_td.html())

            elif label == "Consultati:":
                for tr in pqitems(val_td, 'tr'):
                    if tr.text() == "Forma iniţiatorului":
                        [a] = pqitems(tr, 'a')
                        href = a.attr('href')
                        out['pdf_url'] = href

        return out
