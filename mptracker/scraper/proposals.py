import re
import logging
from datetime import date, datetime
from itertools import groupby
from collections import defaultdict
from pyquery import PyQuery as pq
from werkzeug.urls import url_decode
from mptracker.scraper.common import (
    Scraper, pqitems, get_cdep_id, sanitize, url_args, GenericModel)
from mptracker.common import fix_local_chars


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Proposal(GenericModel):
    pass


class Activity:

    def __init__(self, date, location, html):
        self.date = date
        self.location = location
        self.html = html


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


def parse_proposal_number(number_txt):
    m = re.match(
        r'^(?P<prefix>[\D]*)'
        r'(?P<index>\d{1,4})/'
        r'(\d{2}[-.]\d{2}[-.])?(?P<year>\d{4})$',
        number_txt,
    )
    if m is None:
        raise RuntimeError("Can't parse number %r" % number_txt)
    groups = m.groupdict()
    return (groups['prefix'].strip(), "{index}/{year}".format(**groups))


class ProposalScraper(Scraper):

    mandate_proposal_url = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                            'idm={idm}&leg={leg}&cam=2&pag=2&idl=1&prn=0&par=')

    list_url = 'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam={cam}'

    def list_proposals(self, cam):
        list_url = self.list_url.format(cam=cam)
        list_url += '&anp=2014'
        page = self.fetch_url(list_url)
        table = page.find('p[align=center]').next()
        for tr in pqitems(table, 'tr[valign=top]'):
            td_list = tr.find('td')
            link = td_list.eq(1).find('a')
            args = url_args(link.attr('href'))
            assert args.get('cam', type=int) == cam
            slug = 'senate' if cam == 1 else 'cdep'

            rv = {
                'cdeppk_' + slug: args.get('idp', type=int),
                'title': td_list.eq(2).text(),
            }

            number_txt = link.text().lower().strip()
            (prefix, number) = parse_proposal_number(number_txt)
            if cam == 2:
                if rv['cdeppk_cdep'] in [9542, 9543, 12822, 12868]:
                    continue  # duplicate proposals in cdep.ro db

                if prefix in ['pl', 'pl-x']:
                    rv['number_cdep'] = number
                elif prefix == 'bp':
                    rv['number_bpi'] = number
                elif prefix == 'l':
                    rv['number_senate'] = number
                else:
                    raise RuntimeError("Can't parse number %r" % number_txt)

            yield rv

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

        proposals.update(self.fetch_extra_proposals())

        return list(proposals.values())

    def fetch_extra_proposals(self):
        proposal = Proposal(14203, None)
        self.fetch_proposal_details(proposal)
        yield proposal.cdeppks, proposal

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
            p = Proposal(*cdeppks)
            yield p

    def classify_status(self, text):
        if 'LEGE' in text:
            return 'approved'
        elif u'procedură legislativă încetată' in text:
            return 'rejected'
        else:
            return 'inprogress'

    def proposal(self, cdeppk_cdep, cdeppk_senate):
        page_cdep = page_senate = None
        if cdeppk_cdep:
            page_cdep = self.fetch_url(
                "http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=%d&cam=2"
                % cdeppk_cdep
            )
        if cdeppk_senate:
            page_senate = self.fetch_url(
                "http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=%d&cam=1"
                % cdeppk_senate
            )

        page = page_cdep or page_senate

        prop = Proposal(sponsorships=[])
        prop.title = pq('.headline', page).text()
        prop.cdeppk_cdep = cdeppk_cdep
        prop.cdeppk_senate = cdeppk_senate
        prop.number_bpi = None
        prop.number_cdep = None
        prop.number_senate = None
        prop.decision_chamber = None
        prop.pdf_url = None
        prop.status = None
        prop.status_text = None

        [hook_td] = pqitems(page, ':contains("Nr. înregistrare")')
        metadata_table = pq(hook_td.parents('table')[-1])
        date_texts = []

        for row in pqitems(metadata_table.children('tr')):
            cols = row.children()
            label = cols.eq(0).text().strip()
            val_td = cols.eq(1) if len(cols) > 1 else None

            if label == "- B.P.I.:":
                txt = val_td.text().split()
                prop.number_bpi = ' '.join(
                    parse_proposal_number(t)[1]
                    for t in txt.split()
                )
                date_texts.append(txt.split()[0])

            elif label == "- Camera Deputatilor:":
                txt = val_td.text()
                prop.number_cdep = parse_proposal_number(txt)[1]
                date_texts.append(txt)

            elif label == "- Senat:":
                txt = val_td.text()
                prop.number_senate = parse_proposal_number(txt)[1]
                date_texts.append(txt)

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
                elif txt == 'Camera Deputatilor + Senatul':
                    prop.decision_chamber = 'common'
                elif txt == '-':
                    prop.decision_chamber = None
                else:
                    logger.warn("Unknown decision_chamber %r", txt)

            elif label == "Stadiu:":
                prop.status_text = val_td.text()
                prop.status = self.classify_status(prop.status_text)

        prop.date = get_date_from_numbers(date_texts)
        assert prop.date is not None, "No date for proposal %r" % \
            (prop.cdeppk_cdep or prop.cdeppk_senate)

        cdep_activity = (self.get_activity(page_cdep)
                         if page_cdep else [])
        senate_activity = (self.get_activity(page_senate)
                           if page_senate else [])
        prop.activity = self.merge_activity(cdep_activity, senate_activity)

        return prop

    def get_activity(self, page):
        activity = []
        headline = page.find(':contains("Derularea procedurii legislative")')
        table = list(headline.parents('table').items())[-1]

        date = None
        seen_data = False
        location = None
        location_countdown = 0
        buffer = []
        ac = None
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
                if ac:
                    activity.append(ac)
                ac = Activity(
                    date=datetime.strptime(date_text, '%d.%m.%Y').date(),
                    location=location,
                    html="",
                )

            last_col = pq(cols[-1])
            if last_col.attr('rowspan'):
                assert location_countdown == 0
                location_countdown = int(last_col.attr('rowspan'))
                location = last_col.text()

            else:
                last_col.find('img[src="/img/spacer.gif"]').remove()
                (last_col.find('img[src="/img/icon_pdf_small.gif"]')
                    .replaceWith('(pdf)'))
                html = last_col.html()
                if html:
                    ac.html += sanitize(html) + '\n'

        if ac:
            activity.append(ac)

        return activity

    def merge_activity(self, activity_cdep, activity_senate):
        if not activity_cdep:
            return activity_senate

        if not activity_senate:
            return activity_cdep

        def activity_chunks(series):
            for _, g in groupby(series, lambda ac: ac.location):
                chunk = list(g)
                start_date = chunk[0].date
                yield (start_date, chunk)

        chunks = (list(activity_chunks(activity_cdep)) +
                  list(activity_chunks(activity_senate)))
        chunks.sort(key=lambda pair: pair[0])
        rv = []
        for _, chunk in chunks:
            rv.extend(chunk)
        return rv
