import logging
import flask

logger = logging.getLogger(__name__)


def create_website_app():
    from mptracker import models
    from mptracker.common import common
    from mptracker.website.pages import pages

    app = flask.Flask(__name__)
    app.config.from_pyfile('../../settings.py', silent=True)
    app._logger = logger
    models.init_app(app)
    app.register_blueprint(common)
    app.register_blueprint(pages)

    if app.config.get('SENTRY_DSN'):
        from raven.contrib.flask import Sentry
        Sentry(app)

    return app

if __name__ == '__main__':
    create_app().run()
