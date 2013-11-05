import os
import logging
import flask
from path import path
from mptracker import models
from mptracker.common import common
from mptracker.questions import questions, questions_manager
from mptracker.pages import pages
from mptracker.auth import auth
from mptracker.admin import admin
from mptracker.placenames import placenames_manager
from mptracker.scraper import scraper_manager
from mptracker.proposals import proposals, proposals_manager
from mptracker.votes import votes, votes_manager


logger = logging.getLogger(__name__)


def configure(app):
    project_root = path(__file__).abspath().parent.parent
    app.config['DATA_DIR'] = str(project_root / '_data')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['PRIVILEGED_EMAILS'] = \
        os.environ.get('PRIVILEGED_EMAILS', '').split()
    app.config['RQ_DEFAULT_URL'] = os.environ.get('REDIS_DSN')
    app.config['MPTRACKER_DUMP_TABLES_FOLDER'] = \
        os.environ.get('MPTRACKER_DUMP_TABLES_FOLDER')
    app.config['MPTRACKER_DUMP_TABLES_EXCLUDE'] = \
        os.environ.get('MPTRACKER_DUMP_TABLES_EXCLUDE')

    app.debug = (os.environ.get('DEBUG') == 'on')
    app.config['SENTRY_DSN'] = os.environ.get('SENTRY_DSN')

    app.config.from_pyfile('../settings.py', silent=True)


def create_app():
    app = flask.Flask(__name__)
    configure(app)
    models.init_app(app)
    app.register_blueprint(common)
    app.register_blueprint(auth)
    app.register_blueprint(pages)
    app.register_blueprint(questions)
    app.register_blueprint(proposals)
    app.register_blueprint(votes)
    admin.init_app(app)
    app._logger = logger
    if app.debug:
        from werkzeug.debug import DebuggedApplication
        app.wsgi_app = DebuggedApplication(app.wsgi_app, evalex=True)
    if app.config.get('SENTRY_DSN'):
        from raven.contrib.flask import Sentry
        Sentry(app)
    return app


def create_manager(app):
    from flask.ext.script import Manager

    manager = Manager(app)

    manager.add_command('db', models.db_manager)
    manager.add_command('questions', questions_manager)
    manager.add_command('placenames', placenames_manager)
    manager.add_command('scraper', scraper_manager)
    manager.add_command('proposals', proposals_manager)
    manager.add_command('votes', votes_manager)

    @manager.command
    def worker():
        from flask.ext.rq import get_worker
        get_worker().work()

    @manager.command
    def requeue_failed():
        from rq import get_failed_queue
        from flask.ext.rq import get_connection
        failed = get_failed_queue(get_connection())
        for job in failed.get_jobs():
            failed.requeue(job.id)

    @manager.command
    def import_people():
        from mptracker.scraper.common import get_cached_session
        from mptracker.scraper.people import PersonScraper
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

    return manager
