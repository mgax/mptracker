import sys
import logging
import uuid
import argparse
import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.login import UserMixin
from mptracker.common import parse_date, TablePatcher


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def uuid_type():
    return db.CHAR(32)


def uuid_column():
    return db.Column(uuid_type(), primary_key=True,
                     default=lambda: str(uuid.uuid4()))


def identity(v):
    return v


db = SQLAlchemy()


class Person(db.Model):
    id = uuid_column()
    name = db.Column(db.String)
    cdep_id = db.Column(db.Integer)

    county_id = db.Column(uuid_type(), db.ForeignKey('county.id'))
    county = db.relationship('County',
        backref=db.backref('people', lazy='dynamic'))

    def __str__(self):
        return "<{p.name}>".format(p=self)

    @classmethod
    def get_or_create_non_mp(cls, name):
        for row in cls.query.filter_by(name=name, cdep_id=None):
            return row
        else:
            logger.info('Creating non-MP %s %r', cls.__name__, name)
            row = cls(name=name)
            db.session.add(row)
            db.session.flush()
            return row


class County(db.Model):
    id = uuid_column()
    name = db.Column(db.String)

    def __str__(self):
        return self.name


class StenoChapter(db.Model):
    id = uuid_column()
    date = db.Column(db.Date, index=True)
    headline = db.Column(db.String)
    serial = db.Column(db.String, index=True)

    @property
    def serial_number(self):
        return self.serial.split('/', 1)[1]


class StenoParagraph(db.Model):
    id = uuid_column()
    text = db.Column(db.Text)
    serial = db.Column(db.String, index=True)

    chapter_id = db.Column(uuid_type(), db.ForeignKey('steno_chapter.id'))
    chapter = db.relationship('StenoChapter',
        backref=db.backref('paragraphs', lazy='dynamic'))

    person_id = db.Column(uuid_type(), db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('steno_paragraphs', lazy='dynamic'))


class Question(db.Model):
    id = uuid_column()
    number = db.Column(db.String)
    date = db.Column(db.Date, index=True)
    title = db.Column(db.String)
    url = db.Column(db.String)
    pdf_url = db.Column(db.String)
    type = db.Column(db.String)
    addressee = db.Column(db.String)
    text = db.Column(db.Text)

    person_id = db.Column(uuid_type(), db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('questions', lazy='dynamic'))

    def __str__(self):
        return "<{q.number}/{q.date}>".format(q=self)


class User(db.Model, UserMixin):
    id = uuid_column()
    email = db.Column(db.String)

    @classmethod
    def get_or_create(cls, email, autosave=True):
        for row in cls.query.filter_by(email=email):
            return row
        else:
            logger.info('Creating %s %r', cls.__name__, email)
            row = cls(email=email)
            if autosave:
                db.session.add(row)
                db.session.commit()
            return row


class PersonMatcher:
    """ Find the right person based on name and cdep_id """

    def __init__(self):
        self.cdep_person = {p.cdep_id: p for p in Person.query}

    def name_bits(self, name):
        return set(name.replace('-', ' ').split())

    def get_person(self, name, cdep_id, strict=False):
        if cdep_id is not None:
            person = self.cdep_person[cdep_id]
            if self.name_bits(person.name) == self.name_bits(name):
                return person
        if strict:
            raise RuntimeError("Could not find a match for %r, %r" %
                               (name, cdep_id))
        return Person.get_or_create_non_mp(name)


db_manager = Manager()


@db_manager.command
def sync():
    db.create_all()


@db_manager.option('alembic_args', nargs=argparse.REMAINDER)
def alembic(alembic_args):
    from alembic.config import CommandLine
    CommandLine().main(argv=alembic_args)


@db_manager.command
def upgrade(revision='head'):
    return alembic(['upgrade', revision])


@db_manager.command
def revision(message=None):
    if message is None:
        message = input('revision name: ')
    return alembic(['revision', '--autogenerate', '-m', message])


@db_manager.option('names', nargs='+')
def drop(names):
    engine = db.get_engine(flask.current_app)
    for name in names:
        table = db.metadata.tables[name]
        print('dropping', name)
        table.drop(engine, checkfirst=True)


@db_manager.command
def flush_steno(no_create=False):
    engine = db.get_engine(flask.current_app)
    for model in [StenoChapter, StenoParagraph]:
        table = model.__table__
        table.drop(engine, checkfirst=True)
        if not no_create:
            table.create(engine)


class TableLoader:

    model_map = {model.__tablename__: model for model in
                 [Person, County, StenoParagraph, StenoChapter, Question]}

    def __init__(self, name):
        self.table_name = name
        self.model = self.model_map[name]
        self.columns = []
        self.encoder = {}
        self.decoder = {}
        for col in self.model.__table__._columns:
            self.columns.append(col.name)
            if isinstance(col.type, db.Date):
                self.encoder[col.name] = lambda v: v.isoformat()
                self.decoder[col.name] = parse_date
            else:
                self.encoder[col.name] = self.decoder[col.name] = identity

    def to_dict(self, row, columns=None):
        if columns is None:
            columns = self.columns
        return {col: self.encoder[col](getattr(row, col)) for col in columns}

    def decode_dict(self, encoded_row):
        return {col: self.decoder[col](encoded_row[col])
                for col in encoded_row}


@db_manager.command
def dump(name, columns=None, number=None):
    if columns:
        columns = columns.split(',')
    loader = TableLoader(name)
    count = 0
    for row in loader.model.query.order_by('id'):
        print(flask.json.dumps(loader.to_dict(row, columns), sort_keys=True))
        count += 1
        if number is not None:
            if count >= int(number):
                break


@db_manager.command
def load(name, update_only=False):
    loader = TableLoader(name)
    patcher = TablePatcher(loader.model, db.session, key_columns=['id'])
    records = (loader.decode_dict(flask.json.loads(line))
               for line in sys.stdin)
    patcher.update(records, create=not update_only)
