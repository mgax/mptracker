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
                'modification_date': extract_modification_date(
                    td_list.eq(3).text()),
            }

            number_txt = link.text().lower().strip()
            (prefix, number) = parse_proposal_number(number_txt)
            if cam == 2:
                if rv['cdeppk_cdep'] in CDEPPK_CDEP_BLACKLIST:
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


class SingleProposalScraper(Scraper):

    def __init__(self, cdeppk_cdep, cdeppk_senate, session=None):
        super().__init__(session)
        self.prop = Proposal(
            cdeppk_cdep=cdeppk_cdep,
            cdeppk_senate=cdeppk_senate,
        )
        self.activity = {'cdep': [], 'senate': []}
        self.sponsorship_bucket = set()

    def set_pk_cdep(self, value):
        assert value is not None
        if self.prop.cdeppk_cdep:
            assert self.prop.cdeppk_cdep == value
        else:
            self.prop.cdeppk_cdep = value

    def set_pk_senate(self, value):
        assert value is not None
        if self.prop.cdeppk_senate:
            assert self.prop.cdeppk_senate == value
        else:
            self.prop.cdeppk_senate = value

    def classify_status(self, text):
        if 'LEGE' in text:
            return 'approved'
        elif u'procedură legislativă încetată' in text:
            return 'rejected'
        else:
            return 'inprogress'

    def scrape_page(self, name):
        prop = self.prop

        if name == 'cdep':
            page = self.fetch_url(
                "http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=%d&cam=2"
                % prop.cdeppk_cdep
            )

        elif name == 'senate':
            page = self.fetch_url(
                "http://www.cdep.ro/pls/proiecte/upl_pck.proiect?idp=%d&cam=1"
                % prop.cdeppk_senate
            )

        else:
            raise RuntimeError

        prop.title = pq('.headline', page).text()
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
                txt = val_td.text()
                prop.number_bpi = ' '.join(
                    parse_proposal_number(t)[1]
                    for t in txt.split()
                )
                date_texts.append(txt.split()[0])

            elif label == "- Camera Deputatilor:":
                txt = val_td.text()
                prop.number_cdep = parse_proposal_number(txt)[1]
                date_texts.append(txt)
                link = val_td.find('a')
                if link:
                    args = url_args(link.attr('href'))
                    assert args.get('cam', '2') == '2'
                    self.set_pk_cdep(args.get('idp', type=int))

            elif label == "- Senat:":
                txt = val_td.text()
                prop.number_senate = parse_proposal_number(txt)[1]
                date_texts.append(txt)
                link = val_td.find('a')
                if link:
                    args = url_args(link.attr('href'))
                    assert args.get('cam') == '1'
                    self.set_pk_senate(args.get('idp', type=int))

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

            elif label == "Initiator:":
                for link in pqitems(val_td, 'a'):
                    args = url_args(link.attr('href'))
                    if args.get('cam', 2, type=int) == 2:
                        cdep_id = (
                            args.get('leg', type=int),
                            args.get('idm', type=int),
                        )
                        self.sponsorship_bucket.add(cdep_id)

        prop.date = get_date_from_numbers(date_texts)
        assert prop.date is not None, "No date for proposal %r" % \
            (prop.cdeppk_cdep or prop.cdeppk_senate)

        self.activity[name] = self.get_activity(page)

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

    def scrape(self):
        visited = set()

        while True:
            available = set()
            if self.prop.cdeppk_cdep:
                available.add('cdep')
            if self.prop.cdeppk_senate:
                available.add('senate')

            if available == visited:
                break

            name = (available - visited).pop()
            self.scrape_page(name)
            visited.add(name)

        prop = self.prop

        prop.activity = self.merge_activity(
            self.activity['cdep'],
            self.activity['senate'],
        )

        prop.modification_date = prop.activity[-1].date

        prop.sponsorships = sorted(self.sponsorship_bucket)

        return prop
