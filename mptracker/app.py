import os
import logging
import flask
from flask.ext.script import Manager
from path import path
from mptracker import models
from mptracker.pages import pages, parse_date


logger = logging.getLogger(__name__)


def configure(app):
    project_root = path(__file__).abspath().parent.parent
    data_dir = project_root / '_data'
    data_dir.mkdir_p()
    db_path = data_dir / 'db.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.debug = (os.environ.get('DEBUG') == 'on')
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        from raven.contrib.flask import Sentry
        Sentry(app, dsn=sentry_dsn)


def create_app():
    app = flask.Flask(__name__)
    configure(app)
    models.db.init_app(app)
    app.register_blueprint(pages)
    app._logger = logger
    return app


manager = Manager(create_app)

manager.add_command('db', models.db_manager)


@manager.command
def import_people():
    from mpscraper.common import get_cached_session
    from mpscraper.people import PersonScraper
    ps = PersonScraper(get_cached_session())
    existing_cdep_ids = set(p.cdep_id for p in models.Person.query)
    new_people = 0
    session = models.db.session
    for person_info in ps.fetch_people():
        if person_info['cdep_id'] not in existing_cdep_ids:
            print('adding person:', person_info)
            p = models.Person(**person_info)
            session.add(p)
            existing_cdep_ids.add(p.cdep_id)
            new_people += 1
    print('added', new_people, 'people')
    session.commit()


def import_steno_day(day):
    from mpscraper.common import get_cached_session
    from mpscraper.steno import StenogramScraper
    http_session = get_cached_session()

    name_bits = lambda name: set(name.replace('-', ' ').split())
    cdep_person = {p.cdep_id: p for p in models.Person.query}

    def get_person(name, cdep_id):
        if cdep_id is not None:
            person = cdep_person[cdep_id]
            if name_bits(person.name) == name_bits(name):
                return person
        return models.Person.get_or_create_non_mp(name)

    session = models.db.session
    steno_scraper = StenogramScraper(http_session)
    steno_day = steno_scraper.fetch_day(day)
    new_paragraphs = 0
    for steno_chapter in steno_day.chapters:
        chapter_ob = models.StenoChapter(date=steno_day.date,
                                         headline=steno_chapter.headline,
                                         serial=steno_chapter.serial)
        session.add(chapter_ob)
        for paragraph in steno_chapter.paragraphs:
            person = get_person(paragraph['speaker_name'],
                                paragraph['speaker_cdep_id'])

            paragraph_ob = models.StenoParagraph(text=paragraph['text'],
                                                 chapter=chapter_ob,
                                                 person=person,
                                                 serial=paragraph['serial'])
            session.add(paragraph_ob)
            new_paragraphs += 1
    print('added', new_paragraphs, 'stenogram paragraphs')
    session.commit()


@manager.command
def import_steno(day=None, stdin=False):
    if stdin:
        import sys
        days = [line.strip() for line in sys.stdin]
    elif day is not None:
        days = [day]
    else:
        raise RuntimeError("Need day or stdin")

    for day in days:
        try:
            import_steno_day(parse_date(day))
            print(day, "ok")
        except Exception as e:
            models.db.session.rollback()
            print(day, "fail", e)
