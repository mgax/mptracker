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

CDEPPK_CDEP_BLACKLIST = [9542, 9543, 12822, 12868, 13812, 13815]


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


def extract_modification_date(txt):
    return date(*[
        int(n) for n in
        reversed(txt.strip().split()[-1].split('.'))
    ])


class ProposalScraper(Scraper):

    mandate_proposal_url = ('http://www.cdep.ro/pls/parlam/structura.mp?'
                            'idm={idm}&leg={leg}&cam=2&pag=2&idl=1&prn=0&par=')

    list_url = 'http://www.cdep.ro/pls/proiecte/upl_pck.lista?cam={cam}'

    def list_proposals(self, cam, year=None):
        list_url = self.list_url.format(cam=cam)
        if year:
            list_url += '&anp=%s' % year
        page = self.fetch_url(list_url)
        table = page.find('p[align=center]').next()
        for tr in pqitems(table, 'tr[valign=top]'):
            td_list = tr.find('td')
            link = td_list.eq(1).find('a')
            args = url_args(link.attr('href'))
            assert args.get('cam', type=int) == cam

            date_txt = td_list.eq(3).text()
            try:
                date = extract_modification_date(date_txt)
            except:
                logger.warn("Can't parse modification date %r" % date_txt)
                continue

            yield {
                'pk': args.get('idp', type=int),
                'chamber': cam,
                'date': date,
            }


    def scrape_proposal_page(self, chamber, pk):
        rv = {}
        url = (
            'http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=%d&cam=%d'
            % (pk, chamber)
        )
        page = self.fetch_url(url)

        if chamber == 1:
            rv['pk_senate'] = pk
        else:
            rv['pk_cdep'] = pk

        rv['title'] = pq('.headline', page).text()
        rv['sponsorship'] = []

        [hook_td] = pqitems(page, ':contains("Nr. înregistrare")')
        metadata_table = pq(hook_td.parents('table')[-1])
        date_texts = []

        for row in pqitems(metadata_table.children('tr')):
            cols = row.children()
            label = cols.eq(0).text().strip()
            val_td = cols.eq(1) if len(cols) > 1 else None

            if label == "- B.P.I.:":
                txt = val_td.text()
                rv['number_bpi'] = ' '.join(
                    parse_proposal_number(t)[1]
                    for t in txt.split()
                )
                date_texts.append(txt.split()[0])

            elif label == "- Camera Deputatilor:":
                txt = val_td.text()
                rv['number_cdep'] = parse_proposal_number(txt)[1]
                date_texts.append(txt)
                link = val_td.find('a')
                if link:
                    args = url_args(link.attr('href'))
                    assert args.get('cam', '2') == '2'
                    rv['pk_cdep'] = args.get('idp', type=int)

            elif label == "- Senat:":
                txt = val_td.text()
                rv['number_senate'] = parse_proposal_number(txt)[1]
                date_texts.append(txt)
                link = val_td.find('a')
                if link:
                    args = url_args(link.attr('href'))
                    assert args.get('cam') == '1'
                    rv['pk_senate'] = args.get('idp', type=int)

            elif label == "Tip initiativa:":
                rv['proposal_type'] = val_td.text()

            elif label == "Consultati:":
                for tr in pqitems(val_td, 'tr'):
                    if tr.text() == "Forma iniţiatorului":
                        [a] = pqitems(tr, 'a')
                        href = a.attr('href')
                        rv['pdf_url'] = href

            elif label == "Camera decizionala:":
                txt = val_td.text()
                if txt == 'Camera Deputatilor':
                    rv['decision_chamber'] = 'cdep'
                elif txt == 'Senatul':
                    rv['decision_chamber'] = 'senat'
                elif txt == 'Camera Deputatilor + Senatul':
                    rv['decision_chamber'] = 'common'
                elif txt == '-':
                    rv['decision_chamber'] = None
                else:
                    logger.warn("Unknown decision_chamber %r", txt)

            elif label == "Stadiu:":
                rv['status_text'] = val_td.text()

            elif label == "Initiator:":
                for link in pqitems(val_td, 'a'):
                    args = url_args(link.attr('href'))
                    if args.get('cam', 2, type=int) == 2:
                        cdep_id = (
                            args.get('leg', type=int),
                            args.get('idm', type=int),
                        )
                        rv['sponsorship'].append(cdep_id)

        rv['date'] = get_date_from_numbers(date_texts)
        assert rv['date'] is not None, "No date for %r %r" % (chamber, pk)

        rv['activity'] = self.get_activity(page)

        return rv

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


class SingleProposalScraper:

    def __init__(self):
        self.prop = Proposal()
        self.activity = {'cdep': [], 'senate': []}
        self.sponsorship_bucket = set()

    def classify_status(self, text):
        if 'LEGE' in text:
            return 'approved'
        elif u'procedură legislativă încetată' in text:
            return 'rejected'
        else:
            return 'inprogress'

    def scrape_page(self, name, result):
        prop = self.prop

        prop.title = result['title']
        prop.number_bpi = result.get('number_bpi')
        prop.number_cdep = result.get('number_cdep')
        prop.number_senate = result.get('number_senate')
        prop.decision_chamber = result.get('decision_chamber')
        prop.pdf_url = result.get('pdf_url')
        prop.status_text = result.get('status_text')
        prop.status = self.classify_status(result['status_text'])
        prop.date = result['date']
        prop.proposal_type = result.get('proposal_type')

        self.activity[name] = result['activity']

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

    def finalize(self):
        prop = self.prop

        prop.activity = self.merge_activity(
            self.activity['cdep'],
            self.activity['senate'],
        )

        prop.modification_date = prop.activity[-1].date

        prop.sponsorships = sorted(self.sponsorship_bucket)

        return prop
