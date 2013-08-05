from datetime import datetime
from contextlib import contextmanager
import tempfile
from path import path


def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()


@contextmanager
def temp_dir():
    tmp = path(tempfile.mkdtemp())
    try:
        yield tmp
    finally:
        tmp.rmtree()
