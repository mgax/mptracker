from path import path
from pyquery import PyQuery as pq


class Scraper(object):

    def fetch_url(self, *args, **kwargs):
        page = pq(*args, parser='html', **kwargs)
        page.make_links_absolute()
        return page


def install_requests_cache():
    import requests_cache
    project_root = path(__file__).abspath().parent.parent
    requests_cache.install_cache(project_root / '_data' / 'http_cache')


def fix_encoding(text):
    return text.encode('latin-1').decode('iso-8859-2')


def pqitems(ob, selector=None):
    cls = type(ob)
    if selector is None:
        found = ob
    else:
        found = ob(selector)
    return (cls(el) for el in found)
