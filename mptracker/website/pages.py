from datetime import date, datetime, timedelta
import functools
import re
import flask
from werkzeug.exceptions import NotFound
import jinja2
from babel.numbers import format_currency
from mptracker import models
from mptracker.common import csv_lines, csv_response, buffer_on_disk
from mptracker.common import parse_date
from mptracker.common import VOTE_LABEL, QUESTION_TYPE_LABEL, PARTY_COLOR
from mptracker.website.dal import DataAccess, LEGISLATURE_2012_START
from mptracker.website.texts import get_text, get_text_list
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


def picture_url(person):
    picture_rel_path = path('pictures/2012') / person.picture_filename
    if (path(flask.current_app.static_folder) / picture_rel_path).isfile():
        return flask.url_for(
            'static',
            filename=picture_rel_path,
        )


def logo_url(party):
    picture_rel_path = path('parties') / party.logo_filename
    if (path(flask.current_app.static_folder) / picture_rel_path).isfile():
        return flask.url_for(
            'static',
            filename=picture_rel_path,
        )


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


@pages.context_processor
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
                label="Politici publice",
            ),
            dict(
                url=flask.url_for('.export_index'),
                section='export',
                label="Export date",
            ),
        ],
        'MP_HA': 10000,
    }


def text_content(name, fold=False, below_fold=False, ns='general'):
    text = get_text(ns, name)

    if fold:
        html = text['content']

    elif below_fold:
        html = text['more_content']

    else:
        html = text['content'] + text['more_content']

    return jinja2.Markup(html)


def text_title(name, ns='general'):
    text = get_text(ns, name)
    return text['title']


@pages.record
def register_text(state):
    state.app.jinja_env.globals.update({
        'text': text_content,
        'text_title': text_title,
    })


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


@pages.route('/_debug')
def debug():
    return flask.render_template('_debug.html', models=models)


@pages.route('/')
def home():
    STATS_SLIDE_COLOR = ['blue', 'green', 'orange']

    migration_list = []
    for item in dal.get_migrations(limit=2):
        person = dal.get_person(item['person']['slug'])
        item['person']['picture_url'] = picture_url(person)
        migration_list.append(item)

    similarity_person = dal.get_person('ponta-victor-viorel')

    stats_name_list = [name for ns, name in get_text_list() if ns == 'stats']

    def stats_detail(name, color):
        stats_text = get_text('stats', name)
        return {
            'background_img': flask.url_for(
                'static',
                filename='img/stats/%s.jpg' % color,
            ),
            'title': stats_text['title'],
            'content': stats_text['content'] + stats_text['more_content'],
            'url': flask.url_for('.stats_page', name=name)
        }

    return flask.render_template('home.html', **{
        'policy_list': dal.get_policy_list(),
        'tacit_approvals_count': dal.get_tacit_approvals_count(),
        'controversy_count': dal.get_controversy_count(),
        'recent_proposals': dal.get_recent_proposals(3),
        'recent_questions': dal.get_recent_questions(3),
        'policy_domains': dal.get_top_policies(),
        'body_class': 'home',
        'tacit_proposal_list': dal.get_policy_tacit_approval_list(limit=3),
        'tacit_proposal_count': dal.get_policy_tacit_approval_count(),
        'controversy_proposal_list': dal.get_policy_controversy_list(limit=3),
        'controversy_proposal_count': dal.get_policy_controversy_count(),
        'migration_list': migration_list,
        'migration_count': dal.get_migration_count(),
        'similarity_person': similarity_person.get_main_details(),
        'person_list': dal.search_person_by_name(''),
        'stats_list': [
            stats_detail(name, STATS_SLIDE_COLOR[i])
            for i, name in enumerate(sorted(stats_name_list))
        ],
    })


@pages.route('/_votesimilarity')
def home_votesimilarity():
    similarity_person = dal.get_person('ponta-victor-viorel')

    return flask.jsonify({
        'vote_similarity_list': similarity_person.get_voting_similarity_list(),
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
        'breadcrumb': ['Deputați', 'Căutare'],
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
    ctx['breadcrumb'] = ['Deputați', ctx['name']]
    ctx['picture_url'] = picture_url(person)

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
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Contact']
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
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Activitate']
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
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Activitate Locală']
    return flask.render_template('person_local.html', **ctx)


@pages.route('/persoane/<person_slug>/intrebari')
@section('person')
def person_questions(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['question_list'] = person.get_questions()
    ctx['person_slug'] = person_slug
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Întrebări']
    return flask.render_template('person_questions.html', **ctx)


@pages.route('/persoane/<person_slug>/propuneri')
@section('person')
def person_proposals(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['proposal_list'] = person.get_proposals()
    ctx['person_slug'] = person_slug
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Propuneri']
    return flask.render_template('person_proposals.html', **ctx)


@pages.route('/persoane/<person_slug>/voturi')
@section('person')
def person_votes(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['voting_session_list'] = person.get_votes_data()
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Voturi']
    return flask.render_template('person_votes.html', **ctx)


@pages.route('/persoane/<person_slug>/avere')
@section('person')
def person_assets(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['assets'] = person.get_assets_data()
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Avere']
    return flask.render_template('person_assets.html', **ctx)


@pages.route('/persoane/<person_slug>/comparatie')
@section('person')
def person_compare_index(person_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['person_slug'] = person_slug
    ctx.update(person.get_comparison_lists())
    ctx['vote_similarity_list'] = person.get_voting_similarity_list()
    ctx['breadcrumb'] = ['Deputați', ctx['name'], 'Comparație']
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
    attendance_data = lambda row, cls: {
        'class': cls,
        'value': row['attendance_2013'],
        'title': row['committee'],
    }
    ctx['attendance_data'] = (
        [attendance_data(row, 'me') for row in
         ctx['stats']['committee_attendance']] +
        [attendance_data(row, 'other') for row in
         ctx['other']['stats']['committee_attendance']]
    )
    ctx['breadcrumb'] = ['Deputați', 'Comparație între ' + ctx['name'] + ' și ' + ctx['other']['name']]
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
@section('person')
def person_policy(person_slug, policy_slug):
    person = dal.get_person(person_slug)
    ctx = person.get_main_details()
    ctx['policy'] = person.get_policy(policy_slug)
    return flask.render_template('person_policy.html', **ctx)


@pages.route('/persoane/migrari')
@section('person')
def person_migrations():
    migration_list = list(dal.get_migrations())
    return flask.render_template('person_migrations.html', **{
        'migration_list': migration_list,
        'breadcrumb': ['Deputați', 'Migrări'],
    })


@pages.route('/intrebari-interpelari/')
@section('person')
def person_question_index():
    ctx = {
        'question_list': dal.get_policy_question_list(),
    }
    return flask.render_template('question_index.html', **ctx)


@pages.route('/intrebari-interpelari/<uuid:question_id>')
@section('person')
def person_question(question_id):
    question = dal.get_question_details(question_id)
    return flask.render_template('question.html', **{
        'question': question,
        'breadcrumb': ['Întrebări și interpelări'],
    })


@pages.route('/stenograme/<path:serial>')
@section('person')
def transcript_chapter(serial):
    ctx = dal.get_transcript_chapter(serial)
    return flask.render_template('transcript_chapter.html', **ctx)


@pages.route('/persoane/judet/<county_code>')
@section('person')
def person_county(county_code):
    county = dal.get_county(county_code)
    ctx = county.get_details()
    ctx['mandate_list'] = county.get_mandates_data()
    ctx['breadcrumb'] = ['Deputați', ctx['name']]
    return flask.render_template('person_county.html', **ctx)


@pages.route('/partide/')
@section('party')
def party_index():
    seats = [
        dict(r, color=PARTY_COLOR.get(r['party']))
        for r in dal.get_seats()
    ]
    party_list = dal.get_party_list()
    for party in party_list:
        party['logo_url'] = logo_url(dal.get_party(party['short_name']))
    return flask.render_template('party_index.html', **{
        'party_list': party_list,
        'breadcrumb': ['Partide'],
        'seats': seats,
        'seats_total': sum(r['count'] for r in seats),
    })


@pages.route('/partide/<party_short_name>')
@section('party')
def party_detail(party_short_name):
    party = dal.get_party(party_short_name)
    member_count = party.get_member_count()
    seats = {r['party']: r for r in dal.get_seats()}

    return flask.render_template('party_detail.html', **{
        'party': party.get_details(),
        'policy_domains': party.get_top_policies(),
        'breadcrumb': ['Partide', party.get_name()],
        'member_count': member_count,
        'total_members': sum(mc['count'] for mc in member_count),
        'logo_url': logo_url(party),
        'seats': seats.get(party_short_name),
        'seats_total': sum(r['count'] for r in seats.values()),
    })


@pages.route('/partide/<party_short_name>/politici/<policy_slug>')
@section('party')
def party_policy(party_short_name, policy_slug):
    party = dal.get_party(party_short_name)
    policy = party.get_policy(policy_slug)
    return flask.render_template('party_policy.html', **{
        'party': party.get_main_details(),
        'policy': policy,
        'policy_members': party.get_policy_members(policy_slug),
        # the breadcrumb below needs a third parameter, The name of the policy
        'breadcrumb': ['Partide', party.get_name()],
    })


@pages.route('/partide/<party_short_name>/membri/')
@section('party')
def party_members(party_short_name):
    party = dal.get_party(party_short_name)
    return flask.render_template('party_members.html', **{
        'party': party.get_main_details(),
        'members': party.get_members(),
        'breadcrumb': ['Partide', party.get_name(), 'Membri'],
    })


@pages.route('/politici/')
@section('policy')
def policy_index():
    return flask.render_template('policy_index.html', **{
        'policy_list': dal.get_policy_list(),
        'breadcrumb': ['Politici publice'],
    })


@pages.route('/politici/aprobate-tacit')
@section('policy')
def policy_tacit():
    return flask.render_template(
        'policy_tacit.html',
        proposal_list=dal.get_policy_tacit_approval_list(),
    )


@pages.route('/politici/controversate')
@section('policy')
def policy_controversy():
    return flask.render_template(
        'policy_controversy.html',
        proposal_list=dal.get_policy_controversy_list(),
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
        'policy_slug': policy_slug,
        'policy_name': policy_name,
        'proposal_list': dal.get_policy_proposal_list(policy_slug),
        'question_list': dal.get_policy_question_list(policy_slug),
        'active_parties': dal.get_policy_top_parties(policy_slug),
        'breadcrumb': ['Politici publice', policy_name],
        'active_people': dal.search_person_by_policy(policy_slug),
        'committee_list': dal.get_policy_committees(policy_slug),
    }
    return flask.render_template('policy_detail.html', **ctx)


@pages.route('/politici/feed')
@pages.route('/politici/<policy_slug>/feed')
@section('policy')
def policy_proposal_feed(policy_slug=None):
    proposal_list = dal.get_policy_proposal_list(policy_slug)
    proposal_list.reverse()
    def html(p):
        return flask.render_template('policy_feed_item.html', proposal=p)
    atom = flask.render_template(
        'policy_feed.xml',
        policy_name=dal.get_policy(policy_slug)['name'] if policy_slug else None,
        updated=max(
            p['modification_date'] for p in
            proposal_list or [{'modification_date': date.today()}]
        ),
        proposal_list=[
            dict(p, html=html(p))
            for p in proposal_list[:20]
        ],
    )
    return flask.Response(atom, mimetype='application/atom+xml')


@pages.route('/politici/propuneri/')
@section('policy')
def policy_proposal_index():
    ctx = {
        'proposal_list': dal.get_policy_proposal_list(),
        'breadcrumb': ['Politici publice'],
    }
    return flask.render_template('policy_proposal_index.html', **ctx)


@pages.route('/politici/propuneri/<uuid:proposal_id>')
@section('policy')
def policy_proposal(proposal_id):
    proposal = dal.get_proposal_details(proposal_id)
    return flask.render_template('policy_proposal.html', proposal=proposal)


@pages.route('/politici/vot-controversat/<uuid:controversy_id>')
@section('policy')
def vote_controversy(controversy_id):
    ctx = dal.get_vote_controversy(controversy_id)
    return flask.render_template('policy_vote_controversy.html', **ctx)


@pages.route('/politici/comisii/<uuid:committee_id>')
def committee_detail(committee_id):
    ctx = dal.get_committee_details(committee_id)
    return flask.render_template('committee_detail.html', **ctx)


@pages.route('/info/reprezentare_locala', defaults={'name': 'local', 'comments': True})
@pages.route('/info/editorial', defaults={'name': 'editorial', 'comments': True})
@pages.route('/info/cum_functioneaza', defaults={'name': 'cum_functioneaza'})
@pages.route('/info/evolutii_legislative', defaults={'name': 'evolutii_legislative'})
@pages.route('/info/monitorizeaza_deputatul', defaults={'name': 'monitorizeaza_deputatul'})
@pages.route('/info/grupuri_parlamentare', defaults={'name': 'grupuri_parlamentare'})
@pages.route('/info/descarca_datele', defaults={'name': 'descarca_datele'})
@pages.route('/info/contribuie', defaults={'name': 'donations'})
@pages.route('/info/controverse', defaults={'name': 'voting_controversy', 'comments': True})
@pages.route('/info/despre', defaults={'name': 'about', 'comments': True})
@pages.route('/info/echipa', defaults={'name': 'team'})
@pages.route('/info/contact', defaults={'name': 'contact', 'comments': True})
@pages.route('/info/termeni', defaults={'name': 'terms_of_use'})
@pages.route('/articole/parlamentari-la-urne', defaults={'name': 'parlamentari-la-urne', 'ns': 'article'})
@pages.route('/articole/comunicare-parlamente', defaults={'name': 'comunicare-parlamente', 'ns': 'article'})
def text_page(name, ns='general', comments=False):
    text = get_text(ns, name)
    return flask.render_template(
        'text.html',
        title=text['title'],
        text=text['content'] + text['more_content'],
        comments=comments,
    )


@pages.route('/statistici/<name>')
def stats_page(name):
    text = get_text('stats', name)
    if not text['title']:
        flask.abort(404)
    return flask.render_template(
        'text.html',
        title=text['title'],
        text=text['content'] + text['more_content'],
        comments=False,
    )


@pages.route('/export/')
@section('export')
def export_index():
    ctx = {
        'breadcrumb': ['Export de date'],
    }
    return flask.render_template('export.html', **ctx)


@pages.route('/export/membri_grupuri.csv')
@section('export')
def export_group_membership():
    results = dal.get_group_membership(
        day=parse_date(flask.request.args.get('date')) or date.today()
    )

    membership_list = [
        {
            'nume': row['name'],
            'inceput': row['start'].isoformat(),
            'sfarsit': '' if row['end'] is None else row['end'].isoformat(),
            'partid': row['group'],
        }
        for row in results
    ]

    return csv_response(
        csv_lines(['nume', 'inceput', 'sfarsit', 'partid'], membership_list),
    )


@pages.route('/export/migrari.csv')
@section('export')
def export_migrations():
    results = dal.get_group_migrations(
        start=parse_date(flask.request.args['start']),
        end=parse_date(flask.request.args.get('end', '9999-12-31')),
    )

    membership_list = [
        {
            'nume': row['name'],
            'data': row['date'].isoformat(),
            'partid_vechi': row['group_old'],
            'partid_nou': row['group_new'],
        }
        for row in results
    ]

    cols = ['nume', 'data', 'partid_vechi', 'partid_nou']
    return csv_response(csv_lines(cols, membership_list))


@pages.route('/export/mandate_incepute_tarziu.csv', defaults={'rq': 'late_start'})
@pages.route('/export/mandate_incheiate_devreme.csv', defaults={'rq': 'early_end'})
@section('export')
def export_bounded_mandates(rq):
    out_list = [
        {
            'nume': row['name'],
            'partid': row['group'],
            'inceput': row['start'].isoformat(),
            'sfarsit': row['end'].isoformat(),
        }
        for row in dal.get_bounded_mandates(rq)
    ]
    cols = ['nume', 'partid', 'inceput', 'sfarsit']
    return csv_response(csv_lines(cols, out_list))


@pages.route('/export/voturi.csv')
@section('export')
def export_votes():
    cols = ['data', 'cod cdep', 'nume', 'vot', 'vot grup']
    year = flask.request.args.get('an', type=int)
    rows = (
        {
            'data': row['date'].isoformat(),
            'cod cdep': row['cdeppk'],
            'nume': row['name'],
            'vot': VOTE_LABEL.get(row['choice'], ''),
            'vot grup': VOTE_LABEL.get(row['group_choice'], ''),
        }
        for row in dal.get_all_votes(year=year)
    )
    data = buffer_on_disk(csv_lines(cols, rows))
    return csv_response(data)


@pages.route('/export/intrebari.csv')
@section('export')
def export_questions():
    cols = ['data', 'numar', 'tip', 'titlu', 'nume', 'destinatar', 'scor']
    year = flask.request.args.get('an', type=int)
    rows = (
        {
            'data': row['date'].isoformat(),
            'numar': row['number'],
            'tip': QUESTION_TYPE_LABEL[row['type']],
            'titlu': row['title'],
            'nume': row['name'],
            'destinatar': row['addressee'],
            'scor': int(row['local_score']),
        }
        for row in dal.get_all_questions(year=year)
    )
    data = buffer_on_disk(csv_lines(cols, rows))
    return csv_response(data)
