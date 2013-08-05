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


class TablePatcher:

    def __init__(self, model, session, key_columns):
        self.model = model
        self.session = session
        self.key_columns = key_columns
        self.existing = {self.row_key(row): row
                         for row in self.model.query}

    def row_key(self, row):
        return tuple(getattr(row, k) for k in self.key_columns)

    def dict_key(self, record):
        return tuple(record.get(k) for k in self.key_columns)

    def update(self, data):
        for record in data:
            key = self.dict_key(record)
            row = self.existing.get(key)
            if row is None:
                row = self.model()

            for k in record:
                setattr(row, k, record[k])

            self.session.add(row)
            self.existing[key] = row

        self.session.commit()
