import uuid
from flask.ext.sqlalchemy import SQLAlchemy


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
            return cls(name=name)


class StenoSection(db.Model):
    id = uuid_column()
    date = db.Column(db.Date, index=True)
    headline = db.Column(db.String)


class StenoParagraph(db.Model):
    id = uuid_column()
    text = db.Column(db.Text)
    serial = db.Column(db.Integer, index=True)

    section_id = db.Column(uuid_type(), db.ForeignKey('steno_section.id'))
    section = db.relationship('StenoSection',
        backref=db.backref('paragraphs', lazy='dynamic'))

    person_id = db.Column(uuid_type(), db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('steno_paragraphs', lazy='dynamic'))
