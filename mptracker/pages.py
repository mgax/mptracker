from collections import defaultdict
import calendar
from datetime import datetime
import flask
from sqlalchemy.orm import joinedload
from path import path
from mptracker import models
from mptracker.common import parse_date


pages = flask.Blueprint('pages', __name__)




@pages.route('/_crashme')
def crashme():
    raise RuntimeError("Crashing, as requested.")


@pages.route('/_ping')
def ping():
    models.Person.query.count()
    return 'mptracker is ok'


@pages.route('/')
def home():
    return flask.render_template('home.html')


@pages.route('/steno/')
def steno_index():
    people = models.Person.query.order_by('name')
    date_query = models.db.session.query(models.StenoChapter.date)
    steno_days = set(row[0] for row in date_query.distinct())
    return flask.render_template('steno.html', **{
        'steno_days': steno_days,
    })


@pages.route('/person/')
def person_index():
    people = (models.Person.query
                           .join(models.Mandate)
                           .order_by('name'))
    return flask.render_template('person_index.html', **{
        'people': people,
    })


@pages.route('/person/<uuid:person_id>')
def person(person_id):
    person = models.Person.query.get_or_404(person_id)
    mandates = [{
            'id': m.id,
            'cdep_url': m.get_cdep_url(),
            'year': m.year,
            'county_name': m.county.name,
            'chamber_name': m.chamber.name,
            'questions_count': m.questions.count(),
            'paragraphs_count': m.steno_paragraphs.count(),
            'sponsorships_count': m.sponsorships.count(),
            'college': m.college,
            'phone': m.phone,
            'address': m.address,
            'votes': m.votes,
            'votes_percent': m.votes_percent,
            'candidate_party': m.candidate_party,
            'committee_memberships': (m.committee_memberships
                                            .join(models.MpCommittee)
                                            .all()),
            'group_membership': (m.group_memberships
                                        .join(models.MpGroup)
                                        .first()),
        } for m in person.mandates
                         .join(models.Mandate.county)
                         .join(models.Mandate.chamber)
                         .order_by('-year')]
    return flask.render_template('person.html', **{
        'person': person,
        'mandates': mandates,
    })


@pages.route('/committee/')
def committee_index():
    return flask.render_template('committee_index.html', **{
        'committee_list': models.MpCommittee.query.order_by('name').all(),
    })


@pages.route('/committee/<uuid:committee_id>')
def committee(committee_id):
    committee = models.MpCommittee.query.get_or_404(committee_id)
    return flask.render_template('committee.html', **{
        'committee': committee,
        'memberships': (committee.memberships
                                    .join(models.Mandate)
                                    .join(models.Person)
                                    .all()),
    })


@pages.route('/group/')
def group_index():
    return flask.render_template('group_index.html', **{
        'group_list': models.MpGroup.query.order_by('short_name').all(),
    })


@pages.route('/group/<uuid:group_id>')
def group(group_id):
    group = models.MpGroup.query.get_or_404(group_id)
    return flask.render_template('group.html', **{
        'group': group,
        'memberships': (group.memberships
                                .join(models.Mandate)
                                .join(models.Person)
                                .all()),
    })


@pages.route('/steno/<date_str>')
def steno_contents(date_str):
    date_value = parse_date(date_str)
    return flask.render_template('steno_contents.html', **{
        'date': date_value,
        'chapters': models.StenoChapter.query.filter_by(date=date_value),
    })


@pages.route('/steno/<date_str>/<chapter_serial_number>')
def steno_chapter(date_str, chapter_serial_number):
    date_value = parse_date(date_str)
    chapter_serial = date_value.strftime('%Y-%m-%d/') + chapter_serial_number
    chapter = (models.StenoChapter.query
                .filter_by(serial=chapter_serial)
                .first_or_404())
    if chapter.date != date_value:
        flask.abort(404)
    return flask.render_template('steno_chapter.html', **{
        'date': date_value,
        'chapter': chapter,
    })


@pages.route('/committee-summary/<uuid:summary_id>')
def committee_summary(summary_id):
    summary = models.CommitteeSummary.query.get_or_404(summary_id)
    return flask.render_template('committee_summary.html', **{
        'summary': summary,
    })


@pages.route('/debug')
def debug():
    args = flask.request.args
    do = args.get('do')
    if do == 'search-mandate':
        mandate = models.Mandate.query.filter_by(
                        year=int(args['year']),
                        cdep_number=int(args['cdep_number'])).first_or_404()
        url = flask.url_for('.person', person_id=mandate.person_id)
        return flask.redirect(url)

    return flask.render_template('debug.html')


@pages.app_url_defaults
def bust_cache(endpoint, values):
    if endpoint == 'static':
        filename = values['filename']
        file_path = path(flask.current_app.static_folder) / filename
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            key = ('%x' % mtime)[-6:]
            values['t'] = key


@pages.context_processor
def inject_calendar():
    return {
        'calendar_tool_factory': calendar.Calendar,
        'current_year': datetime.today().year,
    }
