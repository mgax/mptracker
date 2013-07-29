import sys
import logging
import uuid
import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def uuid_type():
    return db.CHAR(32)


def uuid_column():
    return db.Column(uuid_type(), primary_key=True,
                     default=lambda: str(uuid.uuid4()))


db = SQLAlchemy()


class Person(db.Model):
    id = uuid_column()
    name = db.Column(db.String)
    cdep_id = db.Column(db.Integer)

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


db_manager = Manager()


@db_manager.command
def sync():
    db.create_all()


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
                 [Person, StenoParagraph, StenoChapter]}

    def __init__(self, name):
        self.table_name = name
        self.model = self.model_map[name]
        self.columns = [c.name for c in self.model.__table__._columns]

    def to_dict(self, row):
        return {col: getattr(row, col) for col in self.columns}


@db_manager.command
def dump(name):
    loader = TableLoader(name)
    for row in loader.model.query.order_by('id'):
        print(flask.json.dumps(loader.to_dict(row), sort_keys=True))


@db_manager.command
def load(name):
    loader = TableLoader(name)
    row_count = 0
    for line in sys.stdin:
        row_data = flask.json.loads(line)
        row = loader.model.query.get(row_data['id'])

        if row is None:
            row = loader.model(**row_data)
            logger.info("Adding row %s", row.id)

        else:
            if loader.to_dict(row) == row_data:
                continue

            logger.info("Updating row %s", row.id)
            for col in row_data:
                setattr(row, row_data[col])

        db.session.add(row)
        row_count += 1

    db.session.commit()
    logger.info("Touched %d rows", row_count)
