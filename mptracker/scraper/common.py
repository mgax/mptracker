import time
from urllib.parse import urlencode, urlparse, parse_qs
from path import path
import requests
from pyquery import PyQuery as pq


project_root = path(__file__).abspath().parent.parent.parent


class Scraper(object):

    def __init__(self, session=None, use_cdep_opener=True):
        self.session = session or requests.Session()
        self.use_cdep_opener = use_cdep_opener

    def fetch_url(self, url, args=None):
        if args:
            if '?' not in url:
                url += '?'
            elif url[-1] not in ['?', '&']:
                url += '&'
            url += urlencode(args)
        kwargs = {'parser': 'html'}
        if self.use_cdep_opener:
            def opener(url):
                resp = self.session.get(url)
                text = resp.content.decode('iso-8859-2')
                # we use utf-16 because the parser's autodetect works fine with it
                return text.encode('utf-16')
            kwargs['opener'] = opener
        page = pq(url, **kwargs)
        page.make_links_absolute()
        return page


def create_throttle(seconds):
    def hook(response, **extra):
        if not getattr(response, 'from_cache', False):
            # logger.debug("Throttle: %s", seconds)
            time.sleep(seconds)
        return response
    return hook


def create_session(cache_name=None, throttle=None):
    if cache_name:
        import requests_cache
        cache_path = project_root / '_data' / cache_name
        session = requests_cache.CachedSession(cache_path)

    else:
        session = requests.Session()

    if throttle:
        session.hooks = {'response': create_throttle(throttle)}

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


def parse_cdep_id(href):
    qs = parse_qs(urlparse(href).query)
    assert qs.get('cam') == ['2']
    year = int(qs['leg'][0])
    number = int(qs['idm'][0])
    return (year, number)
