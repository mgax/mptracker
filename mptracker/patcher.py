from collections import namedtuple
from contextlib import contextmanager
import logging


class RowNotFound(Exception):
    """ Could not find row to match key. """


AddResult = namedtuple('AddResult', ['row', 'is_new', 'is_changed'])


class TablePatcher:

    logger = logging.getLogger(__name__ + '.TablePatcher')
    if not logger.level:
        logger.setLevel(logging.INFO)

    def __init__(self, model, session, key_columns, filter=None):
        from mptracker.models import random_uuid
        self.random_uuid = random_uuid
        self.model = model
        self.table_name = model.__table__.name
        self.session = session
        self.key_columns = key_columns
        self.seen = set()
        self.filter = filter

    def _dict_key(self, record):
        return tuple(record.get(k) for k in self.key_columns)

    def _get_row_for_key(self, key):
        return (
            self.model.query
            .filter_by(**dict(zip(self.key_columns, key)))
            .first()
        )

    def _mark_seen(self, row_id):
        self.seen.add(row_id)

    def ids_to_delete(self):
        self.session.flush()
        query = self.session.query(self.model.id)
        if self.filter:
            query = query.filter_by(**self.filter)
        for row in query:
            row_id = row[0]
            if row_id not in self.seen:
                yield row_id

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

            else:
                raise RowNotFound("Could not find row with key=%r" % key)

        else:
            changes = []
            for k in record:
                old_val = getattr(row, k)
                new_val = record[k]
                if old_val != new_val:
                    self.logger.debug(
                        "Value change for %s %r: %s %r -> %r",
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

        if row.id is None:
            self.session.flush()
        self._mark_seen(row.id)

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
            unseen = list(self.ids_to_delete())
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
