import flask
from flask.ext.script import Manager
from mptracker import models


def create_app():
    app = flask.Flask(__name__)
    models.db.init_app(app)
    return app


manager = Manager(create_app)
