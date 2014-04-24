import time
from datetime import date, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
import logging
import re
import csv
import io
from collections import namedtuple
from path import path
import requests
from werkzeug.urls import url_decode, url_parse
from pyquery import PyQuery as pq
from lxml.html.clean import clean_html
from lxml.html import fromstring, HTMLParser
from lxml import etree
from psycopg2.extras import DateRange
from mptracker.common import parse_date as parse_iso_date

logger = logging.getLogger(__name__)

SCRAPER_PACKAGE = path(__file__).abspath().parent
PROJECT_ROOT = SCRAPER_PACKAGE.parent.parent
SPREADSHEET_CSV_URL_TEMPLATE = (
    'https://docs.google.com/spreadsheet/pub'
    '?key={key}&single=true&gid=0&output=csv'
)
SPREADSHEET_NEW_CSV_URL_TEMPLATE = (
    'https://docs.google.com/spreadsheets/d/{key}/export?format=csv'
)


class Scraper(object):

    use_cdep_opener = True

    def __init__(self, session=None):
        self.session = session or requests.Session()

    def opener(self, url):
        # we need to pass in all the hooks because of a bug in requests 2.0.0
        # https://github.com/kennethreitz/requests/issues/1655
        resp = self.session.get(url, hooks=self.session.hooks)
        if self.use_cdep_opener:
            text = resp.content.decode('iso-8859-2')
            # we use utf-16 because the parser's autodetect works fine with it
            return text.encode('utf-16')
        else:
            return resp.text

    def fetch_url(self, url, args=None):
        if args:
            if '?' not in url:
                url += '?'
            elif url[-1] not in ['?', '&']:
                url += '&'
            url += urlencode(args)
        logger.debug("Fetching URL %s", url)
        page = pq(url, parser='html', opener=self.opener)
        page.make_links_absolute()
        return page


class GenericModel:

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def as_dict(self, keys):
        return {k: getattr(self, k, None) for k in keys}


def create_throttle(seconds):
    def hook(response, **extra):
        if not getattr(response, 'from_cache', False):
            # logger.debug("Throttle: %s", seconds)
            time.sleep(seconds)
        return response
    return hook


def create_session(cache_name=None, throttle=None, counters=False):
    if cache_name:
        import requests_cache
        cache_path = PROJECT_ROOT / '_data' / cache_name
        session = requests_cache.CachedSession(cache_path)

    else:
        session = requests.Session()

    if counters:
        session.counters = counters_data = {
            'requests': 0,
            'bytes': 0,
            'download_time': timedelta(),
        }

        def request_count_hook(response, **extra):
            counters_data['requests'] += 1
            counters_data['bytes'] += len(response.content)
            counters_data['download_time'] += response.elapsed
            return response

        session.hooks['response'].append(request_count_hook)

    if throttle:
        session.hooks['response'].append(create_throttle(throttle))

    return session


def get_cached_session(name='page-cache'):
    return create_session(name)


def pqitems(ob, selector=None):
    cls = type(ob)
    if selector is None:
        found = ob
    else:
        found = ob(selector)
    return [cls(el) for el in found]


def get_cdep_id(href, fail='raise'):
    qs = parse_qs(urlparse(href).query)
    if qs.get('cam') != ['2']:
        if fail == 'raise':
            raise ValueError("cam != 2 (href=%r)" % href)
        elif fail == 'none':
            return None
        else:
            raise RuntimeError("Don't know what fail=%r means" % fail)
    return '%s-%03d' % (int(qs['leg'][0]), int(qs['idm'][0]))


ProfileIdent = namedtuple('ProfileIdent', ['year', 'chamber', 'number'])


def parse_profile_url(href):
    qs = parse_qs(urlparse(href).query)
    year = int(qs['leg'][0])
    chamber = int(qs.get('cam')[0])
    number = int(qs['idm'][0])
    return ProfileIdent(year, chamber, number)


def parse_cdep_id(href):
    (year, chamber, number) = parse_profile_url(href)
    assert chamber == 2
    return (year, number)


def url_args(url):
    return url_decode(url_parse(url).query)


def never(*args, **kwargs):
    return False


def open_scraper_resource(name, mode='rb'):
    return (SCRAPER_PACKAGE / name).open(mode)


def sanitize(html):
    if not html.strip():
        return ''
    parser = HTMLParser(encoding='utf-8')
    try:
        doc = fromstring(html, parser=parser)
    except etree.ParserError:
        return ''
    cleaned = clean_html(doc)
    doc = pq(cleaned)
    if doc.find('body'):
        return doc.find('body').html()
    else:
        return str(doc)


MONTHS = {'ian': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mai': 5, 'iun': 6,
          'iul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'noi': 11, 'dec': 12}


def parse_date(txt, fmt):
    if not txt:
        return None
    if fmt == 'ro_short_month':
        m = re.match(
            r'^(?P<day>\d{1,2}) (?P<month>\w+)\.? (?P<year>\d{4})$',
            txt,
        )
        assert m is not None, "can't parse date: %r" % txt
        return date(
            int(m.group('year')),
            MONTHS[m.group('month')],
            int(m.group('day')),
        )

    elif fmt == 'eu_dots':
        m = re.match(
            r'^(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})$',
            txt,
        )
        assert m is not None, "can't parse date: %r" % txt
        return date(
            int(m.group('year')),
            int(m.group('month')),
            int(m.group('day')),
        )


def create_csv_url(key):
    if key.startswith('0A'):
        return SPREADSHEET_CSV_URL_TEMPLATE.format(key=key)
    else:
        return SPREADSHEET_NEW_CSV_URL_TEMPLATE.format(key=key)


def get_gdrive_csv(key):
    url = create_csv_url(key)
    resp = requests.get(url)
    assert resp.headers['Content-Type'] == 'text/csv'
    text = resp.content.decode('utf-8')
    return csv.DictReader(io.StringIO(text))


def parse_interval(start_txt, end_txt):
    start_date = parse_iso_date(start_txt)
    if end_txt:
        end_date = parse_iso_date(end_txt)
    else:
        end_date = date.max
    return DateRange(start_date, end_date)


class TableRow:

    def __init__(self, headings, tdpq, up_text_values):
        self.headings = headings
        self.tdpq = tdpq
        self.text_values = [td.text() for td in self.tdpq.items()]
        self.text_or_up_values = [
            t or ut for t, ut in
            zip(self.text_values, up_text_values)
        ]

    def _find_column(self, text):
        for n, col_text in enumerate(self.headings):
            if text in col_text:
                return n

    def td(self, header_text):
        col = self._find_column(header_text)
        assert col is not None, "No column named %r" % header_text
        return self.tdpq.eq(col)

    def text(self, header_text, inherit=False):
        col = self._find_column(header_text)
        if col is None:
            return ""
        values = self.text_or_up_values if inherit else self.text_values
        return values[col]


class TableParser:

    def __init__(self, table_html, double_header=False):
        self.table = pq(table_html)
        self.double_header = double_header
        if double_header:
            self.headings = []
            skip_row2_cell = []
            for td in self.table.children('tr').eq(0).children().items():
                n = int(td.attr('colspan') or 1)
                skip = int(td.attr('rowspan') or 1) > 1
                self.headings += [td.text()] * n
                skip_row2_cell += [skip] * n
            offset = 0
            for td in self.table.children('tr').eq(1).children().items():
                while skip_row2_cell[offset]:
                    offset += 1
                self.headings[offset] += ' | ' + td.text()
                offset += 1
        else:
            self.headings = [
                td.text() for td in
                self.table.children('tr').eq(0).children().items()
            ]

    def __iter__(self):
        tr_iter = iter(self.table.children('tr').items())
        next(tr_iter)
        if self.double_header:
            next(tr_iter)
        up_text_values = [""] * len(self.headings)
        for tr in tr_iter:
            table_row = TableRow(
                self.headings,
                tr.children('td'),
                up_text_values,
            )
            up_text_values = table_row.text_or_up_values
            yield table_row


class MembershipParser:

    member_cls = GenericModel
    role_txt = "Funcţia"
    person_txt = "Nume şi prenume"
    start_date_txt = "Membru din"
    end_date_txt = "Membru până"
    date_fmt = 'ro_short_month'
    table_parser_args = {}

    def parse_table(self, table_root):
        for row in TableParser(table_root, **self.table_parser_args):
            name_link = row.td(self.person_txt).find('a')
            yield self.member_cls(
                role=row.text(self.role_txt, inherit=True),
                mp_name=name_link.text(),
                mp_ident=parse_profile_url(name_link.attr('href')),
                start_date=parse_date(
                    row.text(self.start_date_txt),
                    self.date_fmt,
                ),
                end_date=parse_date(
                    row.text(self.end_date_txt),
                    self.date_fmt,
                ),
            )
