import time
from datetime import date, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
import logging
import re
from path import path
import requests
from werkzeug.urls import url_decode, url_parse
from pyquery import PyQuery as pq
from lxml.html.clean import clean_html
from lxml.html import fromstring, HTMLParser
from lxml import etree

logger = logging.getLogger(__name__)

SCRAPER_PACKAGE = path(__file__).abspath().parent
PROJECT_ROOT = SCRAPER_PACKAGE.parent.parent


class Scraper(object):

    def __init__(self, session=None, use_cdep_opener=True):
        self.session = session or requests.Session()
        self.use_cdep_opener = use_cdep_opener

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


def parse_profile_url(href):
    qs = parse_qs(urlparse(href).query)
    year = int(qs['leg'][0])
    chamber = int(qs.get('cam')[0])
    number = int(qs['idm'][0])
    return (year, chamber, number)


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
          'iul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}


def parse_date(txt):
    m = re.match(r'^(?P<day>\d{1,2}) (?P<month>\w+)\.? (?P<year>\d{4})$', txt)
    assert m is not None, "can't parse date: %r" % txt
    return date(
        int(m.group('year')),
        MONTHS[m.group('month')],
        int(m.group('day')),
    )
