import logging
import flask
from path import path

logger = logging.getLogger(__name__)


def create_app():
#    from mptracker import models
    from mptracker.common import common
    from mptracker.questions import questions
    from mptracker.pages import pages
    from mptracker.auth import auth
    #from mptracker.admin import admin
    from mptracker.proposals import proposals
    from mptracker.votes import votes

    app = flask.Flask(__name__)
    app.config.from_pyfile('../settings.py', silent=True)
    app._logger = logger

    #models.init_app(app)
    #app.register_blueprint(common)
    #app.register_blueprint(auth)
    #app.register_blueprint(pages)
    #app.register_blueprint(questions)
    #app.register_blueprint(proposals)
    #app.register_blueprint(votes)
    #admin.init_app(app)

    if app.debug:
        from werkzeug.debug import DebuggedApplication
        app.wsgi_app = DebuggedApplication(app.wsgi_app, evalex=True)

    if app.config.get('SENTRY_DSN'):
        from raven.contrib.flask import Sentry
        Sentry(app)

    return app


def create_rq_manager():
    from flask.ext.script import Manager
    from flask.ext.rq import get_worker, get_connection
    from rq import get_failed_queue

    rq_manager = Manager()

    @rq_manager.command
    def worker():
        """ run a worker process """
        worker = get_worker()
        sentry = flask.current_app.extensions.get('sentry')
        if sentry is not None:
            from rq.contrib.sentry import register_sentry
            register_sentry(sentry.client, worker)
        worker.work()

    @rq_manager.command
    def retry():
        """ retry failed jobs"""
        failed = get_failed_queue(get_connection())
        for job in failed.get_jobs():
            failed.requeue(job.id)

    @rq_manager.command
    def cleanup():
        """ delete failed jobs"""
        failed = get_failed_queue(get_connection())
        failed.empty()

    return rq_manager


def create_manager(app):
    from flask.ext.script import Manager
    from mptracker import models
    from mptracker.questions import questions_manager
    from mptracker.placenames import placenames_manager
    from mptracker.scraper import scraper_manager
    from mptracker.proposals import proposals_manager
    from mptracker.votes import votes_manager
    from mptracker.policy import policy_manager

    manager = Manager(app)

    manager.add_command('db', models.db_manager)
    manager.add_command('rq', create_rq_manager())
    manager.add_command('questions', questions_manager)
    manager.add_command('placenames', placenames_manager)
    manager.add_command('scraper', scraper_manager)
    manager.add_command('proposals', proposals_manager)
    manager.add_command('votes', votes_manager)
    manager.add_command('policy', policy_manager)

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
