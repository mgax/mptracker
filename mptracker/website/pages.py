import functools
import flask
from werkzeug.exceptions import NotFound
from mptracker import models
from mptracker.website.dal import DataAccess
from path import path

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
    return flask.render_template('home.html', **{
        'recent_proposals': dal.get_recent_proposals(),
        'recent_questions': dal.get_recent_questions(),
    })


@pages.route('/persoane/')
@section('person')
def person_index():
    mandates_by_county = dal.get_2012_mandates_by_county()
    for county_list in mandates_by_county.values():
        for mandate_info in county_list:
            mandate_info['url'] = flask.url_for(
                '.person_detail',
                person_slug=mandate_info['person_slug'],
            )

    return flask.render_template('person_index.html', **{
        'county_name_map': dal.get_county_name_map(),
        'mandates_by_county': mandates_by_county,
    })


@pages.route('/persoane/_search')
def person_index_search():
    query = flask.request.args['q']
    results = [
        {
            'name': person['name'],
            'url': flask.url_for('.person_detail', person_slug=person['slug']),
        }
        for person in dal.search_person(query)
    ]
    return flask.jsonify(results=results)


@pages.route('/persoane/<person_slug>')
@section('person')
def person_detail(person_slug):
    person = dal.get_person(person_slug, missing=NotFound)
    ctx = person.get_details()
    ctx['person_slug'] = person_slug
    ctx['activitychart_data'] = person.get_activitychart_data()

    if 'picture_filename' in ctx:
        picture_rel_path = path('mandate-pictures') / ctx['picture_filename']
        if (path(flask.current_app.static_folder) / picture_rel_path).isfile():
            ctx['picture_url'] = flask.url_for(
                'static',
                filename=picture_rel_path,
            )

    for item in ctx['recent_activity']:
        if item['type'] == 'proposal':
            item['url'] = flask.url_for(
                '.policy_proposal',
                proposal_id=item['proposal_id'],
            )

        elif item['type'] == 'question':
            item['url'] = flask.url_for(
                '.person_question',
                question_id=item['question_id'],
            )

    return flask.render_template('person_detail.html', **ctx)


@pages.route('/persoane/<person_slug>/local')
@section('person')
def person_local(person_slug):
    person = dal.get_person(person_slug, missing=NotFound)
    ctx = person.get_main_details()
    ctx.update(person.get_local_activity())
    ctx['person_slug'] = person_slug
    return flask.render_template('person_local.html', **ctx)


@pages.route('/persoane/<person_slug>/intrebari')
@section('person')
def person_questions(person_slug):
    person = dal.get_person(person_slug, missing=NotFound)
    ctx = person.get_main_details()
    ctx['question_list'] = person.get_questions()
    ctx['person_slug'] = person_slug
    return flask.render_template('person_questions.html', **ctx)


@pages.route('/persoane/<person_slug>/propuneri')
@section('person')
def person_proposals(person_slug):
    person = dal.get_person(person_slug, missing=NotFound)
    ctx = person.get_main_details()
    ctx['proposal_list'] = person.get_proposals()
    ctx['person_slug'] = person_slug
    return flask.render_template('person_proposals.html', **ctx)


@pages.route('/persoane/<person_slug>/voturi')
@section('person')
def person_votes(person_slug):
    person = dal.get_person(person_slug, missing=NotFound)
    ctx = person.get_main_details()
    ctx['voting_session_list'] = person.get_votes_data()
    return flask.render_template('person_votes.html', **ctx)


@pages.route('/persoane/intrebari-interpelari/<uuid:question_id>')
def person_question(question_id):
    return flask.render_template('person_question.html', **{
        'question': dal.get_question_details(question_id),
    })


@pages.route('/persoane/judet/<uuid:county_id>')
@section('person')
def person_county(county_id):
    county = dal.get_county(county_id, missing=NotFound)
    ctx = county.get_details()
    ctx['mandate_list'] = county.get_mandates_data()
    return flask.render_template('person_county.html', **ctx)


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
@pages.route('/politici/altele')
@section('policy')
def policy_detail(policy_id=None):
    if policy_id is None:
        policy_name = "Altele"
    else:
        policy_name = dal.get_policy(policy_id, missing=NotFound)['name']
    ctx = {
        'policy_name': policy_name,
        'proposal_list': dal.get_policy_proposal_list(policy_id),
    }
    return flask.render_template('policy_detail.html', **ctx)


@pages.route('/politici/propuneri/<uuid:proposal_id>')
@section('policy')
def policy_proposal(proposal_id):
    proposal = dal.get_proposal_details(proposal_id, missing=NotFound)
    return flask.render_template('policy_proposal.html', proposal=proposal)
