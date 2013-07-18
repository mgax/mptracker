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
