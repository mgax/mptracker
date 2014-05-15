import functools
import flask
from werkzeug.exceptions import NotFound
import jinja2
from babel.numbers import format_currency
from mptracker import models
from mptracker.common import csv_lines
from mptracker.website.dal import DataAccess
from path import path

dal = DataAccess(missing=NotFound)

pages = flask.Blueprint('pages', __name__)


def section(name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            flask.g.section = name
            return func(*args, **kwargs)
        return wrapper
    return decorator


@pages.app_template_filter('maybe_url')
def maybe_url(text, url):
    if url:
        return (
            jinja2.Markup('<a href="%s">%s</a>')
            % (jinja2.escape(url), jinja2.escape(text))
        )
    else:
        return jinja2.escape(text)


@pages.app_template_filter('link_for')
def link_for(*args, **kwargs):
    return maybe_url(args[0], flask.url_for(*args[1:], **kwargs))


@pages.app_template_filter('money')
def money(value, currency):
    return format_currency(
        value,
        format='¤¤\xa0#,##0',
        currency=currency,
        locale='ro',
    )


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
            dict(
                url=flask.url_for('.export_index'),
                section='export',
                label="Export date",
            ),
        ],
        'MP_HA': 10000,
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
        'tacit_approvals_count': dal.get_tacit_approvals_count(),
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
        'policy_list': dal.get_policy_list(),
    })


@pages.route('/persoane/_search_by_name')
def person_index_search_name():
    name_query = flask.request.args['name_query']
    results = [
        {
            'name': person['name'],
            'url': flask.url_for('.person_detail', person_slug=person['slug']),
        }
        for person in dal.search_person_by_name(name_query)
    ]
    return flask.jsonify(results=results)


@pages.route('/persoane/_search_by_policy')
def person_index_search_policy():
    policy_slug = flask.request.args['policy_slug']
    results = dal.search_person_by_policy(policy_slug)
    for person in results:
        person['url'] = flask.url_for(
            '.person_detail',
            person_slug=person['slug'],
        )
    return flask.jsonify(results=results)


@pages.route('/persoane/_search_by_contracts')
def person_index_search_contracts():
    contracts_query = flask.request.args['contracts_query']
    results = dal.search_person_by_contracts(contracts_query)
    for person in results:
        person['url'] = flask.url_for(
            '.person_detail',
            person_slug=person['slug'],
        )
    return flask.jsonify(results=results)


def _add_activity_url(person_slug, item):
    if item['type'] == 'proposal':
        item['url'] = flask.url_for(
            '.policy_proposal',
            proposal_id=item['proposal_id'],
        )

    elif item['type'] in ['question', 'interpelation']:
        item['url'] = flask.url_for(
            '.person_question',
            question_id=item['question_id'],
        )

    elif item['type'] == 'speech':
        item['url'] = flask.url_for(
            '.transcript_chapter',
            serial=item['chapter_serial'],
        ) + '#' + item['serial_id']


@pages.route('/persoane/<person_slug>')
@section('person')
def person_detail(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_details()
    ctx['person_slug'] = person_slug
    ctx['stats'] = person.get_stats()
    ctx['activitychart_data'] = person.get_activitychart_data()
    ctx['group_history'] = person.get_group_history()
    ctx['policy_domains'] = person.get_top_policies()

    if 'picture_filename' in ctx:
        picture_rel_path = path('mandate-pictures') / ctx['picture_filename']
        if (path(flask.current_app.static_folder) / picture_rel_path).isfile():
            ctx['picture_url'] = flask.url_for(
                'static',
                filename=picture_rel_path,
            )

    ctx['recent_activity'] = person.get_recent_activity(limit=3, limit_each=2)
    for item in ctx['recent_activity']:
        _add_activity_url(person_slug, item)

    return flask.render_template('person_detail.html', **ctx)


@pages.route('/persoane/<person_slug>/contact')
@section('person')
def person_contact(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_details()
    ctx['person_slug'] = person_slug
    return flask.render_template('person_contact.html', **ctx)


@pages.route('/persoane/<person_slug>/activitate')
@section('person')
def person_activity(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['activitychart_data'] = person.get_activitychart_data()
    ctx['group_history'] = person.get_group_history()
    ctx['recent_activity'] = person.get_recent_activity()
    ctx['person_slug'] = person_slug
    for item in ctx['recent_activity']:
        _add_activity_url(person_slug, item)
    return flask.render_template('person_activity.html', **ctx)


@pages.route('/persoane/<person_slug>/local')
@section('person')
def person_local(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx.update(person.get_local_activity())
    ctx['person_slug'] = person_slug
    return flask.render_template('person_local.html', **ctx)


@pages.route('/persoane/<person_slug>/intrebari')
@section('person')
def person_questions(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['question_list'] = person.get_questions()
    ctx['person_slug'] = person_slug
    return flask.render_template('person_questions.html', **ctx)


@pages.route('/persoane/<person_slug>/propuneri')
@section('person')
def person_proposals(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['proposal_list'] = person.get_proposals()
    ctx['person_slug'] = person_slug
    return flask.render_template('person_proposals.html', **ctx)


@pages.route('/persoane/<person_slug>/voturi')
@section('person')
def person_votes(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['voting_session_list'] = person.get_votes_data()
    return flask.render_template('person_votes.html', **ctx)


@pages.route('/persoane/<person_slug>/avere')
@section('person')
def person_assets(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['assets'] = person.get_assets_data()
    return flask.render_template('person_assets.html', **ctx)


@pages.route('/persoane/<person_slug>/comparatie')
@section('person')
def person_compare_index(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['person_slug'] = person_slug
    ctx.update(person.get_comparison_lists())
    return flask.render_template('person_compare_index.html', **ctx)


@pages.route('/persoane/<person_slug>/comparatie/<other_person_slug>')
@section('person')
def person_compare(person_slug, other_person_slug):
    person = dal.get_person(person_slug)
    other_person = dal.get_person(other_person_slug)
    ctx = person.get_main_details()
    ctx['person_slug'] = person_slug
    ctx['stats'] = person.get_stats()
    ctx['other'] = other_person.get_main_details()
    ctx['other']['person_slug'] = other_person_slug
    ctx['other']['stats'] = other_person.get_stats()
    ctx['similarity'] = person.get_voting_similarity(other_person)
    return flask.render_template('person_compare.html', **ctx)


@pages.route('/persoane/<person_slug>/stenograme')
@section('person')
def person_transcript_list(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['transcript_list'] = person.get_transcript_list()
    for item in ctx['transcript_list']:
        _add_activity_url(person_slug, item)

    return flask.render_template('person_transcript_list.html', **ctx)


@pages.route('/persoane/<person_slug>/stenograme/<path:serial>')
@section('person')
def person_transcript(person_slug, serial):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['transcript'] = dal.get_transcript(serial)
    return flask.render_template('person_transcript.html', **ctx)


@pages.route('/persoane/<person_slug>/politici/<policy_slug>')
def person_policy(person_slug, policy_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['policy'] = person.get_policy(policy_slug)
    return flask.render_template('person_policy.html', **ctx)


@pages.route('/intrebari-interpelari/<uuid:question_id>')
def person_question(question_id):
    return flask.render_template('question.html', **{
        'question': dal.get_question_details(question_id),
    })


@pages.route('/stenograme/<path:serial>')
def transcript_chapter(serial):
    ctx = dal.get_transcript_chapter(serial)
    return flask.render_template('transcript_chapter.html', **ctx)


@pages.route('/persoane/judet/<county_code>')
@section('person')
def person_county(county_code):
    county = dal.get_county(county_code)
    ctx = county.get_details()
    ctx['mandate_list'] = county.get_mandates_data()
    return flask.render_template('person_county.html', **ctx)


@pages.route('/partide/')
@section('party')
def party_index():
    return flask.render_template('party_index.html', **{
        'party_list': dal.get_party_list(),
    })


@pages.route('/partide/<party_short_name>')
@section('party')
def party_detail(party_short_name):
    party = dal.get_party_details(party_short_name)
    return flask.render_template('party_detail.html', **{
        'party': party,
    })


@pages.route('/politici/')
@section('policy')
def policy_index():
    return flask.render_template('policy_index.html', **{
        'policy_list': dal.get_policy_list(),
    })

@pages.route('/politici/aprobate-tacit')
@section('policy')
def policy_tacit():
    return flask.render_template(
        'policy_tacit.html',
        proposal_list=dal.get_policy_tacit_approval_list(),
    )

@pages.route('/politici/<policy_slug>')
@pages.route('/politici/altele')
@section('policy')
def policy_detail(policy_slug=None):
    if policy_slug is None:
        policy_name = "Altele"
    else:
        policy_name = dal.get_policy(policy_slug)['name']
    ctx = {
        'policy_name': policy_name,
        'proposal_list': dal.get_policy_proposal_list(policy_slug),
        'question_list': dal.get_policy_question_list(policy_slug),
    }
    return flask.render_template('policy_detail.html', **ctx)


@pages.route('/politici/propuneri/<uuid:proposal_id>')
@section('policy')
def policy_proposal(proposal_id):
    proposal = dal.get_proposal_details(proposal_id)
    return flask.render_template('policy_proposal.html', proposal=proposal)


@pages.route('/export')
@section('export')
def export_index():
    return flask.render_template('export.html')


@pages.route('/export/componenta.csv')
@section('export')
def export_mp_list():
    persons = []
    for party in dal.get_parties():
        members = [
            {
                'partid': party.get_name(),
                'nume': person.mandate.person.name_first_last,
            }
            for person in party.get_members()
        ]
        persons += members

    return flask.Response(
        csv_lines(['partid', 'nume'], persons),
        mimetype='text/csv',
    )
