from os import environ
import logging

DEBUG = (environ.get('DEBUG') == 'on')

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(
    logging.INFO if DEBUG else logging.WARN)
logging.getLogger('alembic').setLevel(logging.INFO)


import sqlalchemy as sa
from alembic import context


def run_migrations_offline():
    """ Run migrations in 'offline' mode. No engine needed. """
    url = environ['DATABASE']
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """ Run migrations in 'online' mode. Need engine and connection. """
    import sys
    from path import path
    sys.path.append(str(path(__file__).parent.parent))
    from mptracker import models

    import flask
    app = flask.Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE']
    models.db.init_app(app)

    with app.app_context():
        context.configure(connection=models.db.session.connection(),
                          target_metadata=models.db.metadata)
        context.run_migrations()
        models.db.session.commit()


if context.is_offline_mode():
    run_migrations_offline()

else:
    run_migrations_online()
