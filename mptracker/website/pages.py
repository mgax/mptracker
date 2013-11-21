import flask
from mptracker import models

pages = flask.Blueprint('pages', __name__)


@pages.app_context_processor
def inject_nav_links():
    return {
        'nav_link_list': [
            dict(
                url=flask.url_for('.person_index'),
                label="Deputați",
            ),
            dict(
                url=flask.url_for('.party_index'),
                label="Partide",
            ),
            dict(
                url=flask.url_for('.policy_index'),
                label="Domenii de politici publice",
            ),
        ],
    }


@pages.route('/_crashme', methods=['GET', 'POST'])
def crashme():
    if flask.request.method == 'POST':
        raise RuntimeError("Crashing, as requested.")
    else:
        return '<form method="post"><button type="submit">err</button></form>'


@pages.route('/_ping')
def ping():
    models.Person.query.count()
    return 'mptracker is ok'


@pages.route('/')
def home():
    return flask.render_template('home.html')


@pages.route('/persoane/')
def person_index():
    return flask.render_template('layout.html')


@pages.route('/partide/')
def party_index():
    return flask.render_template('layout.html')


@pages.route('/politici/')
def policy_index():
    return flask.render_template('layout.html')
