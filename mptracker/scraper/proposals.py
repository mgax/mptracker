import re
import logging
from pyquery import PyQuery as pq
from werkzeug.urls import url_decode
from mptracker.scraper.common import Scraper, pqitems, get_cdep_id
from mptracker.common import fix_local_chars


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ProposalScraper(Scraper):

    mandate_proposal_url = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                            'idm={idm}&leg={leg}&cam=2&pag=2&idl=1&prn=0&par=')

    def fix_name(self, name):
        return fix_local_chars(re.sub(r'[\s\-]+', ' ', name))

    def fetch_from_mp_pages(self, mandate_cdep_id_list):
        proposals = {}
        for mandate_cdep_id in mandate_cdep_id_list:
            for cdeppks, proposal_url in \
                    self.fetch_mp_proposals(mandate_cdep_id):
                if cdeppks in proposals:
                    proposal_data = proposals[cdeppks]
                    assert proposal_data['url'] == proposal_url
                else:
                    proposal_data = self.fetch_proposal_details(proposal_url)
                    assert proposal_data['url'] == proposal_url
                    proposal_data['cdeppk_cdep'] = cdeppks[0]
                    proposal_data['cdeppk_senate'] = cdeppks[1]
                    proposal_data['_sponsorships'] = []
                    proposals[cdeppks] = proposal_data
                proposal_data['_sponsorships'].append(mandate_cdep_id)
        return list(proposals.values())

    def fetch_mp_proposals(self, cdep_id):
        (leg, idm) = cdep_id
        url = self.mandate_proposal_url.format(leg=leg, idm=idm)
        page = self.fetch_url(url)
        headline = pqitems(page, ':contains("PL înregistrat la")')
        if not headline:
            return  # no proposals here
        table = pq(headline[0].parents('table')[-1])
        rows = iter(pqitems(table, 'tr'))
        assert "PL înregistrat la" in next(rows).text()
        assert "Camera Deputaţilor" in next(rows).text()
        for row in rows:
            cols = pqitems(row, 'td')
            def cdeppk(col):
                href = col.find('a').attr('href') or '?'
                val = url_decode(href.split('?', 1)[1]).get('idp')
                return int(val) if val else None
            cdeppks = (cdeppk(cols[1]), cdeppk(cols[2]))
            link = pqitems(row, 'a')[0]
            url = link.attr('href')
            if 'cam=' not in url:
                assert '?' in url
                url += '&cam=2'
            yield cdeppks, url

    def fetch_proposal_details(self, url):
        page = self.fetch_url(url)
        out = {
            'title': pq('.headline', page).text(),
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

            elif label == "Consultati:":
                for tr in pqitems(val_td, 'tr'):
                    if tr.text() == "Forma iniţiatorului":
                        [a] = pqitems(tr, 'a')
                        href = a.attr('href')
                        out['pdf_url'] = href

            elif label == "Camera decizionala:":
                txt = val_td.text()
                if txt == 'Camera Deputatilor':
                    out['decision_chamber'] = 'cdep'
                elif txt == 'Senatul':
                    out['decision_chamber'] = 'senat'
                else:
                    logger.warn("Unknown decision_chamber %r", txt)

        return out
