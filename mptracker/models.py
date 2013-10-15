# encoding: utf-8

import sys
import logging
import uuid
import argparse
from datetime import datetime
import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.login import UserMixin
from path import path
from mptracker.common import (parse_date, TablePatcher, temp_dir,
                              fix_local_chars)
from mptracker.dbutil import JsonString
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm.collections import attribute_mapped_collection

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db = SQLAlchemy()


def random_uuid():
    return str(uuid.uuid4())


def identity(v):
    return v


class Chamber(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    slug = db.Column(db.Text, index=True)
    name = db.Column(db.Text)


class Person(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    name = db.Column(db.Text)
    year_born = db.Column(db.Integer)
    education = db.Column(db.Text)
    website_url = db.Column(db.Text)
    blog_url = db.Column(db.Text)
    email_value = db.Column(db.Text)
    facebook_url = db.Column(db.Text)
    twitter_url = db.Column(db.Text)

    @property
    def emails(self):
        return (self.email_value or '').split()

    @emails.setter
    def emails(self, values):
        assert isinstance(values, list), "Please supply a list of emails"
        self.email_value = ' '.join(values) if value else None

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s>" % self


class MpGroup(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    name = db.Column(db.Text)
    short_name = db.Column(db.Text)


class MpGroupMembership(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    role = db.Column(db.Text)

    mandate_id = db.Column(UUID, db.ForeignKey('mandate.id'), nullable=False)
    mandate = db.relationship('Mandate',
        backref=db.backref('group_memberships', lazy='dynamic'))

    mp_group_id = db.Column(UUID, db.ForeignKey('mp_group.id'), nullable=False)
    mp_group = db.relationship('MpGroup',
        backref=db.backref('memberships', lazy='dynamic'))


class MpCommittee(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    name = db.Column(db.Text)


class MpCommitteeMembership(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    role = db.Column(db.Text)

    mandate_id = db.Column(UUID, db.ForeignKey('mandate.id'), nullable=False)
    mandate = db.relationship('Mandate',
        backref=db.backref('committee_memberships', lazy='dynamic'))

    mp_committee_id = db.Column(UUID, db.ForeignKey('mp_committee.id'),
                                nullable=False)
    mp_committee = db.relationship('MpCommittee',
        backref=db.backref('memberships', lazy='dynamic'))


class Mandate(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    year = db.Column(db.Integer)
    cdep_number = db.Column(db.Integer)
    minority = db.Column(db.Boolean)
    constituency = db.Column(db.Integer)
    college = db.Column(db.Integer)
    votes = db.Column(db.Integer)
    votes_percent = db.Column(db.Numeric)
    candidate_party = db.Column(db.Text)
    address = db.Column(db.Text)
    phone = db.Column(db.Text)

    person_id = db.Column(UUID, db.ForeignKey('person.id'), nullable=False)
    person = db.relationship('Person',
        backref=db.backref('mandates', lazy='dynamic'))

    chamber_id = db.Column(UUID, db.ForeignKey('chamber.id'), nullable=False)
    chamber = db.relationship('Chamber')

    county_id = db.Column(UUID, db.ForeignKey('county.id'))
    county = db.relationship('County')

    def get_cdep_url(self):
        return ("http://www.cdep.ro/pls/parlam/structura.mp"
                "?idm={m.cdep_number}&cam=2&leg={m.year}".format(m=self))

    def __str__(self):
        return "{m.person} ({m.year})".format(m=self)


class County(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    name = db.Column(db.Text)
    geonames_code = db.Column(db.Integer)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s>" % self


class TranscriptChapter(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    date = db.Column(db.Date, index=True)
    headline = db.Column(db.Text)
    serial = db.Column(db.Text, index=True)

    @property
    def serial_number(self):
        return self.serial.split('/', 1)[1]


class Transcript(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    text = db.Column(db.Text)
    serial = db.Column(db.Text, index=True)

    chapter_id = db.Column(UUID, db.ForeignKey('transcript_chapter.id'))
    chapter = db.relationship('TranscriptChapter',
        backref=db.backref('transcripts', lazy='dynamic'))

    mandate_id = db.Column(UUID, db.ForeignKey('mandate.id'))
    mandate = db.relationship('Mandate',
        backref=db.backref('transcripts', lazy='dynamic'))


class Question(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    number = db.Column(db.Text)
    date = db.Column(db.Date, index=True)
    title = db.Column(db.Text)
    url = db.Column(db.Text)
    pdf_url = db.Column(db.Text)
    type = db.Column(db.Text)
    method = db.Column(db.Text)
    addressee = db.Column(db.Text)

    def __str__(self):
        return "{q.number}/{q.date}".format(q=self)

    def __repr__(self):
        return "<%s>" % self

    text_row = db.relationship('OcrText', lazy='eager', uselist=False,
                    primaryjoin='Question.id==foreign(OcrText.id)',
                    cascade='all')

    def _get_text_row(self):
        if self.text_row is None:
            self.text_row = OcrText(parent='question')
        return self.text_row

    @property
    def text(self):
        return self._get_text_row().text

    @text.setter
    def text(self, value):
        self._get_text_row().text = value

    @classmethod
    def query_by_key(cls, key):
        return (cls.query
                   .join(Ask)
                   .join(Ask.meta)
                   .filter(Meta.key == key)
                   .group_by(cls.id))


class Ask(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)

    question_id = db.Column(UUID, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', lazy='eager',
        backref=db.backref('asked', lazy='dynamic', cascade='all'))

    mandate_id = db.Column(UUID, db.ForeignKey('mandate.id'), nullable=False)
    mandate = db.relationship('Mandate',
        backref=db.backref('asked', lazy='dynamic', cascade='all'))

    match_row = db.relationship('Match', lazy='eager', uselist=False,
                    primaryjoin='Ask.id==foreign(Match.id)',
                    cascade='all')

    @property
    def match(self):
        if self.match_row is None:
            self.match_row = Match(parent='ask')
        return self.match_row

    meta = db.relationship('Meta',
                    collection_class=attribute_mapped_collection('key'),
                    primaryjoin='Ask.id == foreign(Meta.object_id)',
                    cascade='all, delete-orphan')

    def get_meta(self, key):
        if key in self.meta:
            return self.meta[key].value
        else:
            return None

    def set_meta(self, key, value):
        row = self.meta.setdefault(key, Meta(key=key))
        if value is None:
            del self.meta[key]
        else:
            row.value = value

    def get_meta_dict(self):
        return {m.key: m.value for m in self.meta.values()}


class OcrText(db.Model):
    id = db.Column(UUID, primary_key=True)
    parent = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text)

    @classmethod
    def all_ids_for(cls, parent):
        return set(row.id for row in cls.query.filter_by(parent=parent))


class Match(db.Model):
    id = db.Column(UUID, primary_key=True)
    parent = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text)
    score = db.Column(db.Float)

    @classmethod
    def all_ids_for(cls, parent):
        return set(row.id for row in cls.query.filter_by(parent=parent))


class Meta(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    object_id = db.Column(UUID, index=True)
    key = db.Column(db.Text)
    value = db.Column(JsonString)


class CommitteeSummary(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    title = db.Column(db.Text)
    date = db.Column(db.Date)
    committee = db.Column(db.Text)
    pdf_url = db.Column(db.Text)
    text = db.Column(db.Text)



class Sponsorship(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)

    proposal_id = db.Column(UUID, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship('Proposal', lazy='eager',
        backref=db.backref('sponsorships', lazy='dynamic', cascade='all'))

    mandate_id = db.Column(UUID, db.ForeignKey('mandate.id'), nullable=False)
    mandate = db.relationship('Mandate',
        backref=db.backref('sponsorships', lazy='dynamic', cascade='all'))

    match_row = db.relationship('Match', lazy='eager', uselist=False,
                    primaryjoin='Sponsorship.id==foreign(Match.id)',
                    cascade='all')

    @property
    def match(self):
        if self.match_row is None:
            self.match_row = Match(parent='sponsorship')
        return self.match_row


class Proposal(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    title = db.Column(db.Text)
    url = db.Column(db.Text)
    pdf_url = db.Column(db.Text)
    cdeppk_cdep = db.Column(db.Integer)
    cdeppk_senate = db.Column(db.Integer)
    number_cdep = db.Column(db.Text)
    number_senate = db.Column(db.Text)
    number_bpi = db.Column(db.Text)
    date = db.Column(db.Date)
    proposal_type = db.Column(db.Text)

    decision_chamber_id = db.Column(UUID, db.ForeignKey('chamber.id'))
    decision_chamber = db.relationship('Chamber')

    text_row = db.relationship('OcrText', lazy='eager', uselist=False,
                    primaryjoin='Proposal.id==foreign(OcrText.id)',
                    cascade='all')

    def _get_text_row(self):
        if self.text_row is None:
            self.text_row = OcrText(parent='proposal')
        return self.text_row

    @property
    def text(self):
        return self._get_text_row().text

    @text.setter
    def text(self, value):
        self._get_text_row().text = value


class ProposalActivityItem(db.Model):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    date = db.Column(db.Date)
    location = db.Column(db.Text)
    html = db.Column(db.Text)
    order = db.Column(db.Integer)

    proposal_id = db.Column(UUID, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship('Proposal', lazy='eager',
        backref=db.backref('activity', lazy='dynamic', cascade='all'))


class User(db.Model, UserMixin):
    id = db.Column(UUID, primary_key=True, default=random_uuid)
    email = db.Column(db.Text)

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


class LookupError(Exception):
    pass


class MandateLookup:
    """ Find the right person+mandate based on name, year and cdep_number """

    def __init__(self):
        self.cdep_mandate = {(p.year, p.cdep_number): p
                             for p in Mandate.query.join(Mandate.person)}

    def name_bits(self, name):
        return set(fix_local_chars(name).replace('-', ' ').split())

    def find(self, name, year, cdep_number):
        mandate = self.cdep_mandate[year, cdep_number]
        if self.name_bits(mandate.person.name) != self.name_bits(name):
            raise LookupError("Names don't match: %r != %r, %r-%r"
                              % (name, mandate.person.name, year, cdep_number))
        return mandate


def init_app(app):
    db.init_app(app)
    if app.config.get('READONLY'):

        class DatabaseReadonly(RuntimeError):
            pass

        def abort_readonly(*args, **kwargs):
            raise DatabaseReadonly


        if not app.debug:
            @app.errorhandler(DatabaseReadonly)
            def handle_database_readonly(error):
                return (u"Modificările sunt dezactivate "
                        u"temporar. Lucrăm la site.")

        from flask.ext.sqlalchemy import _SignallingSession
        _SignallingSession.commit = abort_readonly


db_manager = Manager()


@db_manager.command
def sync():
    db.create_all()
    alembic(['stamp', 'head'])


@db_manager.option('alembic_args', nargs=argparse.REMAINDER)
def alembic(alembic_args):
    from alembic.config import CommandLine
    CommandLine().main(argv=alembic_args)


@db_manager.command
def upgrade(revision='head'):
    return alembic(['upgrade', revision])


@db_manager.command
def downgrade(revision):
    return alembic(['downgrade', revision])


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


def get_model_map():
    reg = db.Model._decl_class_registry
    models = [reg[k] for k in reg if not k.startswith('_')]
    return {m.__table__.name: m for m in models}


class TableLoader:

    def __init__(self, name):
        self.table_name = name
        self.model = get_model_map()[name]
        self.columns = []
        self.encoder = {}
        self.decoder = {}
        for col in self.model.__table__._columns:
            self.columns.append(col.name)
            if isinstance(col.type, db.Date):
                self.encoder[col.name] = lambda v: v and v.isoformat()
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
def empty(name):
    model = get_model_map()[name]
    model.query.delete()
    db.session.commit()


@db_manager.command
def dump(name, columns=None, number=None, filter=None, _file=sys.stdout):
    if columns:
        columns = columns.split(',')
    loader = TableLoader(name)
    count = 0
    query = loader.model.query

    if filter:
        for filter_spec in filter.split(','):
            if '=' in filter_spec:
                name, value = filter_spec.split('=', 1)
                query = query.filter(getattr(loader.model, name) == value)
            else:
                name = filter_spec
                query = query.filter(getattr(loader.model, name) != None)

    for row in query.order_by('id'):
        flask.json.dump(loader.to_dict(row, columns), _file, sort_keys=True)
        _file.write('\n')
        count += 1
        if number is not None:
            if count >= int(number):
                break

    return count


@db_manager.command
def load(name, include_columns=None, create=True, remove=False,
         _file=sys.stdin):
    if include_columns:
        include_columns = set(include_columns.split(','))
        def filter_record(r):
            return {k: r[k] for k in r if k in include_columns}
    else:
        filter_record = lambda r: r
    loader = TableLoader(name)
    patcher = TablePatcher(loader.model, db.session, key_columns=['id'])
    records = (filter_record(loader.decode_dict(flask.json.loads(line)))
               for line in _file)
    patcher.update(records, create=create, remove=remove)
    db.session.commit()


@db_manager.command
def dump_tables(folder_path=None, xclude=None):
    if folder_path is None:
        folder_path = flask.current_app.config['MPTRACKER_DUMP_TABLES_FOLDER']
        assert folder_path
    if xclude is None:
        xclude = flask.current_app.config.get('MPTRACKER_DUMP_TABLES_EXCLUDE')
    if xclude:
        exclude = xclude.split(',')
    else:
        exclude = []
    folder_path = path(folder_path)
    model_map = get_model_map()
    for name in model_map:
        if name in exclude:
            continue
        print(name, end=' ... ')
        file_name = '%s.json' % name
        file_path = folder_path / file_name
        with open(file_path, 'w', encoding='utf-8') as table_fd:
            count = dump(name, _file=table_fd)
        print(count, 'rows')


@db_manager.command
def load_tables(names, folder_path=None, remove=False):
    if folder_path is None:
        folder_path = flask.current_app.config['MPTRACKER_DUMP_TABLES_FOLDER']
        assert folder_path
    names = names.split(',')
    for name in names:
        file_name = '%s.json' % name
        with open(path(folder_path) / file_name, 'rb') as f:
            print(name, '...')
            load(name, remove=remove, _file=f)


def create_backup(backup_path):
    import zipfile
    with temp_dir() as tmp:
        zip_path = tmp / 'dump.zip'
        zip_archive = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        dump_tables(tmp)
        for file_path in tmp.listdir():
            zip_archive.write(file_path, file_name)
        zip_archive.close()
        zip_path.rename(backup_path)


@db_manager.command
def backup():
    backup_dir = path(flask.current_app.config['BACKUP_DIR'])
    backup_name = datetime.utcnow().strftime('backup-%Y-%m-%d-%H%M%S.zip')
    backup_path = backup_dir / backup_name
    create_backup(backup_path)
    print("Backup at %s (%d bytes)" % (backup_path, backup_path.size))
