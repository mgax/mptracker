from collections import defaultdict
import calendar
from datetime import date, datetime
import flask
from sqlalchemy.orm import joinedload
from path import path
from mptracker import models
from mptracker.common import parse_date


pages = flask.Blueprint('pages', __name__)




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
        'new_count': models.Question.query_by_key('new').count(),
        'bugs_count': models.Question.query_by_key('is_bug').count(),
    })


@pages.route('/transcript/')
def transcript_index():
    people = models.Person.query.order_by('name')
    date_query = models.db.session.query(models.TranscriptChapter.date)
    transcript_days = set(row[0] for row in date_query.distinct())
    return flask.render_template('transcript.html', **{
        'transcript_days': transcript_days,
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
    voting_session_count = (
        models.VotingSession.query
        .filter(models.VotingSession.final == True)
        .count()
    )
    mandates = []
    mandates_query = (
         person.mandates
         .join(models.Mandate.county)
         .join(models.Mandate.chamber)
         .order_by('-year')
    )
    for m in mandates_query:
        final_votes = (
            m.votes
            .join(models.Vote.voting_session)
            .filter(models.VotingSession.final == True)
        )
        loyal_votes = final_votes.filter(models.Vote.loyal == True)
        mandates.append({
            'id': m.id,
            'cdep_url': m.get_cdep_url(),
            'year': m.year,
            'county_name': m.county.name,
            'chamber_name': m.chamber.name,
            'questions_count': m.asked.count(),
            'transcripts_count': m.transcripts.count(),
            'sponsorships_count': m.sponsorships.count(),
            'college': m.college,
            'phone': m.phone,
            'address': m.address,
            'election_votes': m.election_votes,
            'election_votes_percent': m.election_votes_percent,
            'candidate_party': m.candidate_party,
            'committee_memberships': (m.committee_memberships
                                            .join(models.MpCommittee)
                                            .all()),
            'group_memberships': (
                m.group_memberships
                    .order_by(models.MpGroupMembership.interval)
                    .join(models.MpGroup)
                    .all()),
            'votes_attended': final_votes.count(),
            'votes_loyal': loyal_votes.count(),
        })
    return flask.render_template('person.html', **{
        'person': person,
        'mandates': mandates,
        'voting_session_count': voting_session_count,
    })


@pages.route('/mandate/<uuid:mandate_id>/transcripts')
def mandate_transcripts(mandate_id):
    mandate = models.Mandate.query.get_or_404(mandate_id)
    return flask.render_template('mandate_transcripts.html', **{
        'mandate': mandate,
        'transcripts': iter(mandate.transcripts),
    })


@pages.route('/mandate/<uuid:mandate_id>/votes')
def mandate_votes(mandate_id):
    mandate = models.Mandate.query.get_or_404(mandate_id)
    attendance = mandate.votes.count() / models.VotingSession.query.count()
    vote_query = (
        models.db.session
        .query(
            models.Vote,
            models.VotingSession,
            models.MpGroup,
            models.GroupVote,
        )
        .filter(models.Vote.mandate == mandate)
        .join(models.Vote.voting_session)
        .filter(models.VotingSession.final == True)
        .join(models.VotingSession.group_votes)
        .join(models.Vote.mandate)
        .join(models.MpGroupMembership)
        .filter(
            models.MpGroupMembership.interval.contains(
                models.VotingSession.date
            )
        )
        .join(models.MpGroupMembership.mp_group)
        .filter(models.GroupVote.mp_group_id == models.MpGroup.id)
        .order_by(
            models.VotingSession.date.desc(),
            models.VotingSession.cdeppk.desc(),
        )
    )
    vote_list = [
        {
            'voting_session': voting_session,
            'choice': vote.choice,
            'loyal': vote.loyal,
            'group_choice': group_vote.choice,
        }
        for (vote, voting_session, group, group_vote) in vote_query
    ]
    return flask.render_template('mandate_votes.html', **{
        'mandate': mandate,
        'attendance': attendance,
        'vote_list': vote_list,
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
        'memberships': (
            group.memberships
                .filter(
                    models.MpGroupMembership.interval.contains(
                        date.today()))
                .join(models.Mandate)
                .join(models.Person)
                .all()),
    })


@pages.route('/transcript/<date_str>')
def transcript_contents(date_str):
    date_value = parse_date(date_str)
    return flask.render_template('transcript_contents.html', **{
        'date': date_value,
        'chapters': models.TranscriptChapter.query.filter_by(date=date_value),
    })


@pages.route('/transcript/<date_str>/<path:chapter_serial>')
def transcript_chapter(date_str, chapter_serial):
    date_value = parse_date(date_str)
    chapter = (models.TranscriptChapter.query
                .filter_by(serial=chapter_serial)
                .first_or_404())
    if chapter.date != date_value:
        flask.abort(404)
    return flask.render_template('transcript_chapter.html', **{
        'date': date_value,
        'chapter': chapter,
    })


@pages.route('/committee-summary/<uuid:summary_id>')
def committee_summary(summary_id):
    summary = models.CommitteeSummary.query.get_or_404(summary_id)
    return flask.render_template('committee_summary.html', **{
        'summary': summary,
    })


@pages.route('/constituency-map')
def constituency_map():
    return flask.render_template('constituency_map.html')


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
