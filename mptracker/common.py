from datetime import date, datetime
from contextlib import contextmanager
from collections import namedtuple
import subprocess
import logging
import tempfile
import csv
import re
from io import StringIO
from itertools import chain
import flask
from werkzeug.routing import BaseConverter, ValidationError
from flask.ext.rq import job
from babel.dates import format_date
from psycopg2.extras import DateRange
from path import path

MAX_OCR_PAGES = 3

common = flask.Blueprint('common', __name__)


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


class RowNotFound(Exception):
    """ Could not find row to match key. """


AddResult = namedtuple('AddResult', ['row', 'is_new', 'is_changed'])


class TablePatcher:

    logger = logging.getLogger(__name__ + '.TablePatcher')
    logger.setLevel(logging.INFO)

    def __init__(self, model, session, key_columns):
        from mptracker.models import random_uuid
        self.random_uuid = random_uuid
        self.model = model
        self.table_name = model.__table__.name
        self.session = session
        self.key_columns = key_columns
        self._prepare()

    def _row_key(self, row):
        return tuple(getattr(row, k) for k in self.key_columns)

    def _dict_key(self, record):
        return tuple(record.get(k) for k in self.key_columns)

    def _prepare(self):
        self.existing_ids = {}
        query = (
            self.session
            .query(
                self.model.id,
                *[getattr(self.model, k) for k in self.key_columns]
            )
        )
        for row in query:
            row_id = row[0]
            key = row[1:]
            assert row_id
            assert key not in self.existing_ids, "Duplicate key %r" % key
            self.existing_ids[key] = row_id
        self.seen = set()

    def _get_row_for_key(self, key):
        row_id = self.existing_ids.get(key)
        if row_id is None:
            return None
        self.session.flush()
        return self.model.query.get(row_id)

    def _remember_new_row(self, key, row):
        assert row.id
        self.existing_ids[key] = row.id

    def _mark_seen(self, key):
        self.seen.add(key)

    def _get_unseen_ids(self):
        return [self.existing_ids[key] for key in
                set(self.existing_ids) - self.seen]

    def add(self, record, create=True):
        key = self._dict_key(record)
        row = self._get_row_for_key(key)
        is_new = is_changed = False

        if row is None:
            if create:
                row = self.model(id=record.get('id') or self.random_uuid())
                self.logger.info("Adding %s %r", self.table_name, key)
                is_new = is_changed = True
                self.session.add(row)
                self._remember_new_row(key, row)

            else:
                raise RowNotFound("Could not find row with key=%r" % key)

        else:
            changes = []
            for k in record:
                old_val = getattr(row, k)
                new_val = record[k]
                if old_val != new_val:
                    self.logger.debug("Value change for %s %r: %s %r != %r",
                                 self.table_name, key, k, old_val, new_val)
                    changes.append(k)

            if changes:
                self.logger.info("Updating %s %r %s",
                                 self.table_name, key, ','.join(changes))
                is_changed = True

        if is_changed:
            for k in record:
                setattr(row, k, record[k])

        self._mark_seen(key)

        return AddResult(row, is_new, is_changed)

    @contextmanager
    def process(self, autoflush=None, remove=False):
        counters = {'n_add': 0, 'n_update': 0,
                    'n_remove': 0, 'n_ok': 0, 'total': 0}

        def add(record, create=True):
            result = self.add(record, create=create)

            counters['total'] += 0
            if autoflush and counters['total'] % autoflush == 0:
                self.session.flush()

            if result.is_new:
                counters['n_add'] += 1

            elif result.is_changed:
                counters['n_update'] += 1

            else:
                counters['n_ok'] += 1

            return result

        self.seen.clear()

        yield add

        if remove:
            unseen = self._get_unseen_ids()
            if unseen:
                unseen_items = (
                    self.model.query
                    .filter(self.model.id.in_(unseen))
                )
                unseen_items.delete(synchronize_session=False)
                counters['n_remove'] += len(unseen)

        self.session.flush()
        self.logger.info("%s: created %d, updated %d, removed %d, found ok %d.",
                         self.table_name,
                         counters['n_add'], counters['n_update'],
                         counters['n_remove'], counters['n_ok'])

    def update(self, data, create=True, remove=False):
        with self.process(autoflush=1000, remove=remove) as add:
            for record in data:
                add(record, create=create)


@job
def ocr_url(url, max_pages=MAX_OCR_PAGES):
    from mptracker.scraper.common import create_session

    pdf_cache_name = flask.current_app.config.get('MPTRACKER_PDF_CACHE')
    http_session = create_session(cache_name=pdf_cache_name, throttle=0.5)

    with temp_dir() as tmp:
        pdf_data = http_session.get(url).content
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
