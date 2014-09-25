from datetime import date, datetime
from contextlib import contextmanager
import subprocess
import tempfile
import csv
import re
import math
from io import StringIO
from itertools import chain
import hashlib
import unicodedata
import flask
from werkzeug.routing import BaseConverter, ValidationError
from werkzeug.urls import url_decode, url_parse
from werkzeug.wsgi import FileWrapper
from flask.ext.rq import job
from babel.dates import format_date
from psycopg2.extras import DateRange
from path import path

MAX_OCR_PAGES = 3

common = flask.Blueprint('common', __name__)

VOTE_LABEL = {
    'yes': "da",
    'no': "nu",
    'abstain': "abținere",
    'novote': "\u2014",  # em-dash
}

QUESTION_TYPE_LABEL = {
    'question': "întrebare",
    'interpelation': "interpelare",
    'proposal': "propunere legislativă",
    'speech': "luare de cuvânt",
}


PARTY_COLOR = {
    "Indep.": "#eee",
    "Mino.": "#888",
    "PC-PLR": "#3e99ff",
    "PDL": "#ff962d",
    "PNL": "#e9e900",
    "PP-DD": "#5a167b",
    "PSD": "#f00",
    "UDMR": "#005900",
}


PARTY_ORDER = [
    'PP-DD',
    'PSD',
    'PC-PLR',
    'Mino.',
    'Indep.',
    'UDMR',
    'PNL',
    'PDL',
]


POLICY_COLOR = {
  'interne':               '#CCC537',
  'it':                    '#D7553B',
  'drepturile-omului':     '#487AAA',
  'educatie':              '#A08F5A',
  'ue':                    '#D2BA62',
  'sanatate':              '#A0C176',
  'agricultura':           '#2B3B53',
  'economie':              '#EF8D32',
  'cultura':               '#2CACC2',
  'finante':               '#67AEAF',
  'aparare':               '#A6ABA4',
  'transporturi':          '#ACAE38',
  'externe':               '#009B89',
  'administratie-publica': '#1F7C92',
  'munca':                 '#DE2B32',
  'other':                 '#CCCCCC',
}

CHAMBER_NAME = {
    0: "comună",
    1: "senat",
    2: "camera deputaților",
}


class UuidConverter(BaseConverter):

    def to_python(self, value):
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
                    r'[0-9a-f]{4}-[0-9a-f]{12}$', value) is None:
            raise ValidationError
        return value


@common.record
def register_url_converters(state):
    app = state.app
    app.url_map.converters['uuid'] = UuidConverter


@common.app_template_filter('datefmt')
def datefmt(value):
    if value in [date.min, date.max]:
        return ""
    return format_date(value, 'd MMMM y', locale='ro')


@common.app_url_defaults
def bust_cache(endpoint, values):
    if endpoint == 'static':
        filename = values['filename']
        file_path = path(flask.current_app.static_folder) / filename
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            key = ('%x' % mtime)[-6:]
            values['t'] = key


@common.record
def inject_constants(state):
    state.app.jinja_env.globals.update({
        'VOTE_LABEL': VOTE_LABEL,
        'QUESTION_TYPE_LABEL': QUESTION_TYPE_LABEL,
        'PARTY_COLOR': PARTY_COLOR,
        'POLICY_COLOR': POLICY_COLOR,
        'CHAMBER_NAME': CHAMBER_NAME,
        'POSITION_CATEGORY_TITLE': {
          'minister': "ministru",
          'permanent-bureau': "membru al biroului permanent",
          'committee-president': "președinte de comisie parlamentară",
        },
    })


@common.app_template_filter('percent')
def percent(value):
    fmt = "%.0f%%" if (.1 < value < .9) else "%.1f%%"
    return fmt % (value * 100)


def parse_date(date_str):
    return date_str and datetime.strptime(date_str, '%Y-%m-%d').date()


def parse_date_range(date_range_str):
    if not date_range_str:
        return None
    m = re.match(r'^\[(?P<lower>\S+), (?P<upper>\S+)\)$', date_range_str)
    return DateRange(
        parse_date(m.group('lower')),
        parse_date(m.group('upper')),
    )


def fix_local_chars(txt):
    return (txt.replace("ş", "ș").replace("Ş", "Ș")
               .replace("ţ", "ț").replace("Ţ", "Ț"))


@contextmanager
def temp_dir():
    tmp = path(tempfile.mkdtemp())
    try:
        yield tmp
    finally:
        tmp.rmtree()


@job
def ocr_url(url, max_pages=MAX_OCR_PAGES):
    from mptracker.scraper.common import create_session

    pdf_cache_name = flask.current_app.config.get('MPTRACKER_PDF_CACHE')
    http_session = create_session(cache_name=pdf_cache_name, throttle=0.5)

    with temp_dir() as tmp:
        resp = http_session.get(url)
        if resp.status_code != 200:
            raise RuntimeError("PDF download failure (%d) at %r"
                               % (resp.status_code, url))
        pdf_data = resp.content
        pdf_path = tmp / 'document.pdf'
        with pdf_path.open('wb') as f:
            f.write(pdf_data)
        subprocess.check_call(['pdfimages', pdf_path, tmp / 'img'])

        pages = []
        for image_path in sorted(tmp.listdir('img-*'))[:MAX_OCR_PAGES]:
            subprocess.check_call(['tesseract',
                                   image_path, image_path,
                                   '-l', 'ron'],
                                  stderr=subprocess.DEVNULL)
            text = (image_path + '.txt').text()
            pages.append(text)

        return pages


def csv_lines(cols, rows):
    out = StringIO()
    writer = csv.DictWriter(out, cols)
    header = dict(zip(cols, cols))
    for r in chain([header], rows):
        writer.writerow(r)
        yield out.getvalue()
        out.seek(out.truncate(0))


def model_to_dict(model, namelist):
    rv = {}
    for name in namelist:
        rv[name] = getattr(model, name)
    return rv


def url_args(url):
    return url_decode(url_parse(url).query)


def buffer_on_disk(data_iter):
    tmp = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
    for block in data_iter:
        tmp.write(block)
    tmp.flush()
    tmp.seek(0)
    return FileWrapper(tmp)


def iter_file(f, buffer_size=65536):
    while True:
        chunk = f.read(buffer_size)
        if not chunk:
            return
        yield chunk


def calculate_md5(chunk_iter):
    md5 = hashlib.md5()
    for chunk in chunk_iter:
        md5.update(chunk)
    return md5.hexdigest()


class DateAwareJSONEncoder(flask.json.JSONEncoder):

    def default(self, o):
        if isinstance(o, date):
            return o.isoformat()

        return super().default(o)


@common.record
def override_json_encoder(state):
    state.app.json_encoder = DateAwareJSONEncoder


def generate_slug(text, unique=lambda v: True):
    normalized = unicodedata.normalize('NFKD', text).strip().lower()
    no_spaces = re.sub(r'\s+', '-', normalized)
    base_slug = re.sub(r'[^a-z0-9-]', '', no_spaces)
    for n in range(100):
        rv = '%s-%s' % (base_slug, n) if n > 0 else base_slug
        if unique(rv):
            return rv
    else:
        raise RuntimeError("Could not find a unique slug, giving up.")


def almost_eq(a, b, eps=1e-6):
    return abs(1 - a/b) < eps


def csv_response(data):
    debug = flask.current_app.config.get('EXPORT_DEBUG')
    return flask.Response(data, mimetype='text/plain' if debug else 'text/csv')
