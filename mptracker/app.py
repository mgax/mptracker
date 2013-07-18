import flask
from flask.ext.script import Manager
from path import path
from mptracker import models


def configure(app):
    project_root = path(__file__).abspath().parent.parent
    data_dir = project_root / '_data'
    data_dir.mkdir_p()
    db_path = data_dir / 'db.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path


def create_app():
    app = flask.Flask(__name__)
    configure(app)
    models.db.init_app(app)
    return app


manager = Manager(create_app)


@manager.command
def syncdb():
    models.db.create_all()


@manager.command
def import_people():
    from mpscraper.common import install_requests_cache
    from mpscraper.people import PersonScraper
    install_requests_cache()
    ps = PersonScraper()
    session = models.db.session
    for person_info in ps.fetch_people():
        p = models.Person(**person_info)
        session.add(p)
    session.commit()
