import pytest
import flask
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def random_uuid():
    return str(uuid.uuid4())


class Thing(db.Model):
    id = db.Column(db.String, primary_key=True, default=random_uuid)
    code = db.Column(db.String)
    number = db.Column(db.Integer)
    name = db.Column(db.String)


@pytest.fixture
def db_app(request):
    app = flask.Flask('__main__')
    db.init_app(app)
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    request.addfinalizer(ctx.pop)
    return app


@pytest.fixture
def patcher(db_app):
    from mptracker.patcher import TablePatcher
    return TablePatcher(Thing, db.session, key_columns=['code'])


@pytest.fixture
def patcher_twin_key(db_app):
    from mptracker.patcher import TablePatcher
    return TablePatcher(Thing, db.session, key_columns=['code', 'number'])


def test_empty_input(patcher):
    patcher.update([])
    assert list(Thing.query) == []


def test_insert_new_records(patcher):
    records = [{'code': 'an', 'name': "Anne"},
               {'code': 'bo', 'name': "Bob"}]
    patcher.update(records)
    assert sorted([t.name for t in Thing.query]) == ["Anne", "Bob"]


def test_update_existing_records(patcher):
    records = [{'code': 'an', 'name': "Anne"},
               {'code': 'bo', 'name': "Bob"}]
    patcher.update(records)
    records[0]['name'] = "Annette"
    patcher.update(records)
    assert sorted([t.name for t in Thing.query]) == ["Annette", "Bob"]


def test_remove_extra_records(patcher):
    records = [{'code': 'an', 'name': "Anne"},
               {'code': 'bo', 'name': "Bob"}]
    patcher.update(records)
    patcher.update(records[:1], remove=True)
    assert sorted([t.name for t in Thing.query]) == ["Anne"]


def test_remove_extra_records_honors_filter(db_app):
    records = [{'code': 'an', 'number': 1, 'name': "Anne"},
               {'code': 'bo', 'number': 1, 'name': "Bob"},
               {'code': 'cl', 'number': 2, 'name': "Claire"},
               {'code': 'da', 'number': 2, 'name': "Dan"}]
    from mptracker.patcher import TablePatcher
    filter_patcher = TablePatcher(
        Thing,
        db.session,
        key_columns=['code'],
        filter={'number': 1},
    )
    filter_patcher.update(records)
    filter_patcher.update(records[:1], remove=True)
    assert sorted([t.name for t in Thing.query]) == ["Anne", "Claire", "Dan"]


def test_refuse_to_create_records(patcher):
    from mptracker.patcher import RowNotFound
    records = [{'code': 'an', 'name': "Anne"}]
    with pytest.raises(RowNotFound):
        patcher.update(records, create=False)


def test_twin_natural_key(patcher_twin_key):
    records = [{'code': 'an', 'number': 1, 'name': "Anne"},
               {'code': 'bo', 'number': 2, 'name': "Bob"}]
    patcher_twin_key.update(records)
    records[0]['name'] = "Annette"
    patcher_twin_key.update(records)
    assert sorted([t.name for t in Thing.query]) == ["Annette", "Bob"]


def test_patcher_add_returns_row(patcher):
    row1 = patcher.add({'code': 'an', 'name': "Anne"}).row
    row2 = patcher.add({'code': 'an', 'name': "Annette"}).row
    assert row1 == row2
