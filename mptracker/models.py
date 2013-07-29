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
