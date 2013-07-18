import flask
from flask.ext.script import Manager


def create_app():
    app = flask.Flask(__name__)
    return app


manager = Manager(create_app)


if __name__ == '__main__':
    manager.run()
