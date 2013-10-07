import re
import logging
from datetime import date, datetime
from pyquery import PyQuery as pq
from werkzeug.urls import url_decode
from mptracker.scraper.common import Scraper, pqitems, get_cdep_id
from mptracker.common import fix_local_chars


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Proposal:

    def __init__(self, cdeppk_cdep, cdeppk_senate):
        self.cdeppk_cdep = cdeppk_cdep
        self.cdeppk_senate = cdeppk_senate
        self.sponsorships = []

    @property
    def cdeppks(self):
        return (self.cdeppk_cdep, self.cdeppk_senate)


class Activity:
    pass


def get_date_from_numbers(numbers):
    rv = None
    for n in numbers:
        if n:
            m = re.search(r'(?P<day>\d{2})[.\-]'
                          r'(?P<month>\d{2})[.\-]'
                          r'(?P<year>\d{4})', n)
            if m is not None:
                new_date = date(int(m.group('year')),
                                int(m.group('month')),
                                int(m.group('day')))
                if rv is None or new_date < rv:
                    rv = new_date
    return rv


class ProposalScraper(Scraper):

    mandate_proposal_url = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                            'idm={idm}&leg={leg}&cam=2&pag=2&idl=1&prn=0&par=')

    def fix_name(self, name):
        return fix_local_chars(re.sub(r'[\s\-]+', ' ', name))

    def fetch_from_mp_pages(self, mandate_cdep_id_list):
        proposals = {}
        for mandate_cdep_id in mandate_cdep_id_list:
            for prop in self.fetch_mp_proposals(mandate_cdep_id):
                if prop.cdeppks in proposals:
                    prop = proposals[prop.cdeppks]
                else:
                    self.fetch_proposal_details(prop)
                    proposals[prop.cdeppks] = prop
                prop.sponsorships.append(mandate_cdep_id)
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
            p = Proposal(*cdeppks)
            p.url = url
            yield p

    def fetch_proposal_details(self, prop):
        page = self.fetch_url(prop.url)
        prop.title = pq('.headline', page).text()
        prop.number_bpi = None
        prop.number_cdep = None
        prop.number_senate = None
        prop.decision_chamber = None
        prop.pdf_url = None

        [hook_td] = pqitems(page, ':contains("Nr. înregistrare")')
        metadata_table = pq(hook_td.parents('table')[-1])
        for row in pqitems(metadata_table.children('tr')):
            cols = row.children()
            label = cols.eq(0).text().strip()
            val_td = cols.eq(1) if len(cols) > 1 else None

            if label == "- B.P.I.:":
                prop.number_bpi = val_td.text()

            elif label == "- Camera Deputatilor:":
                prop.number_cdep = val_td.text()

            elif label == "- Senat:":
                prop.number_senate = val_td.text()

            elif label == "Tip initiativa:":
                prop.proposal_type = val_td.text()

            elif label == "Consultati:":
                for tr in pqitems(val_td, 'tr'):
                    if tr.text() == "Forma iniţiatorului":
                        [a] = pqitems(tr, 'a')
                        href = a.attr('href')
                        prop.pdf_url = href

            elif label == "Camera decizionala:":
                txt = val_td.text()
                if txt == 'Camera Deputatilor':
                    prop.decision_chamber = 'cdep'
                elif txt == 'Senatul':
                    prop.decision_chamber = 'senat'
                else:
                    logger.warn("Unknown decision_chamber %r", txt)

        prop.date = get_date_from_numbers([prop.number_bpi,
                                         prop.number_cdep,
                                         prop.number_senate])
        assert prop.date is not None, "No date for proposal %r" % prop.url

        prop.activity = self.get_activity(page)

    def get_activity(self, page):
        activity = []
        headline = page.find(':contains("Derularea procedurii legislative")')
        table = list(headline.parents('table').items())[-1]

        date = None
        seen_data = False
        location = None
        location_countdown = 0
        for row in table.children().items():
            if location_countdown > 0:
                location_countdown -= 1

            cols = row.children()

            date_text = cols.eq(0).text()
            if date_text == 'Data':
                seen_data = True
                continue
            elif not seen_data:
                continue

            if date_text:
                date = datetime.strptime(date_text, '%d.%m.%Y').date()

            last_col = pq(cols[-1])
            if last_col.attr('rowspan'):
                assert location_countdown == 0
                location_countdown = int(last_col.attr('rowspan'))
                location = last_col.text()

            else:
                last_col.find('img[src="/img/spacer.gif"]').remove()
                html = last_col.html()
                if html:
                    ac = Activity()
                    ac.date = date
                    ac.location = location
                    ac.html = html.strip()
                    activity.append(ac)

        return activity
