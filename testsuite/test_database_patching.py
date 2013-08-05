import pytest
import flask
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Thing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    from mptracker.common import TablePatcher
    return TablePatcher(Thing, db.session, key_columns=['code'])


@pytest.fixture
def patcher_twin_key(db_app):
    from mptracker.common import TablePatcher
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


def test_twin_natural_key(patcher_twin_key):
    records = [{'code': 'an', 'number': 1, 'name': "Anne"},
               {'code': 'bo', 'number': 2, 'name': "Bob"}]
    patcher_twin_key.update(records)
    records[0]['name'] = "Annette"
    patcher_twin_key.update(records)
    assert sorted([t.name for t in Thing.query]) == ["Annette", "Bob"]
