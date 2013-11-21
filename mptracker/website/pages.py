import functools
import flask
from mptracker import models
from mptracker.website.dal import DataAccess

dal = DataAccess()

pages = flask.Blueprint('pages', __name__)


def section(name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            flask.g.section = name
            return func(*args, **kwargs)
        return wrapper
    return decorator


@pages.app_context_processor
def inject_nav_links():
    return {
        'nav_link_list': [
            dict(
                url=flask.url_for('.person_index'),
                section='person',
                label="Deputați",
            ),
            dict(
                url=flask.url_for('.party_index'),
                section='party',
                label="Partide",
            ),
            dict(
                url=flask.url_for('.policy_index'),
                section='policy',
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
@section('person')
def person_index():
    return flask.render_template('person_index.html')


@pages.route('/persoane/_search')
def person_index_search():
    query = flask.request.args['q']
    results = [
        {'name': person.name}
        for person in dal.search_person(query)
    ]
    return flask.jsonify(results=results)


@pages.route('/partide/')
@section('party')
def party_index():
    return flask.render_template('layout.html')


@pages.route('/politici/')
@section('policy')
def policy_index():
    return flask.render_template('layout.html')
