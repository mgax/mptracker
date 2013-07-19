import flask
from flask.ext.script import Manager
from path import path
from mptracker import models
from mptracker.pages import pages


def configure(app):
    project_root = path(__file__).abspath().parent.parent
    data_dir = project_root / '_data'
    data_dir.mkdir_p()
    db_path = data_dir / 'db.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.debug = True


def create_app():
    app = flask.Flask(__name__)
    configure(app)
    models.db.init_app(app)
    app.register_blueprint(pages)
    return app


manager = Manager(create_app)


@manager.command
def syncdb():
    models.db.create_all()


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


@manager.command
def import_steno():
    from datetime import date
    from mpscraper.common import get_cached_session
    from mpscraper.steno import StenogramScraper

    name_bits = lambda name: set(name.replace('-', ' ').split())
    def check_name_bits(a, b):
        assert name_bits(a).issubset(name_bits(b)), (a, b)

    session = models.db.session
    cdep_person = {p.cdep_id: p for p in models.Person.query}
    steno_scraper = StenogramScraper(get_cached_session())
    steno_day = steno_scraper.fetch_day(date(2013, 6, 10))
    new_paragraphs = 0
    for steno_section in steno_day.sections:
        for paragraph in steno_section.paragraphs:
            p = cdep_person[paragraph['speaker_cdep_id']]
            check_name_bits(p.name, paragraph['speaker_name'])
            s = models.Stenogram(person=p, text=paragraph['text'])
            session.add(s)
            new_paragraphs += 1
    print('added', new_paragraphs, 'stenogram paragraphs')
    session.commit()
