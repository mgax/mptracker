from collections import namedtuple
from contextlib import contextmanager
import logging


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
                    self.logger.debug(
                        "Value change for %s %r: %s %r != %r",
                        self.table_name, key, k, old_val, new_val,
                    )
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
        self.logger.info(
            "%s: created %d, updated %d, removed %d, found ok %d.",
            self.table_name,
            counters['n_add'], counters['n_update'],
            counters['n_remove'], counters['n_ok'],
        )

    def update(self, data, create=True, remove=False):
        with self.process(autoflush=1000, remove=remove) as add:
            for record in data:
                add(record, create=create)
