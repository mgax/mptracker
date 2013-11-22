import functools
import flask
from werkzeug.exceptions import NotFound
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


@pages.app_template_filter('percent')
def percent(value):
    return "%.0f%%" % (value * 100)


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
        {
            'name': person['name'],
            'url': flask.url_for('.person_detail', person_id=person['id']),
        }
        for person in dal.search_person(query)
    ]
    return flask.jsonify(results=results)


@pages.route('/persoane/<uuid:person_id>')
@section('person')
def person_detail(person_id):
    person = dal.get_person(person_id, missing=NotFound)
    ctx = {'person_name': person['name']}
    ctx.update(dal.get_mandate2012_details(person_id))
    return flask.render_template('person_detail.html', **ctx)


@pages.route('/partide/')
@section('party')
def party_index():
    return flask.render_template('party_index.html', **{
        'party_list': dal.get_party_list(),
    })


@pages.route('/partide/<uuid:party_id>')
@section('party')
def party_detail(party_id):
    party = dal.get_party_details(party_id, missing=NotFound)
    return flask.render_template('party_detail.html', **{
        'party': party,
    })


@pages.route('/politici/')
@section('policy')
def policy_index():
    return flask.render_template('policy_index.html', **{
        'policy_list': dal.get_policy_list(),
    })


@pages.route('/politici/<uuid:policy_id>')
@section('policy')
def policy_detail(policy_id):
    policy = dal.get_policy(policy_id, missing=NotFound)
    ctx = {
        'policy_name': policy['name'],
        'proposal_list': dal.get_policy_proposal_list(policy_id),
    }
    return flask.render_template('policy_detail.html', **ctx)


@pages.route('/politici/propuneri/<uuid:proposal_id>')
@section('policy')
def policy_proposal(proposal_id):
    proposal = dal.get_proposal(proposal_id, missing=NotFound)
    ctx = {
        'proposal_title': proposal['title'],
    }
    return flask.render_template('policy_proposal.html', **ctx)
