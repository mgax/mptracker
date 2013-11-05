from datetime import date
from collections import defaultdict
import logging
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

votes_manager = Manager()

votes = flask.Blueprint('votes', __name__)


@votes.route('/votes/')
def index():
    voting_sessions = (
        models.VotingSession.query
            .order_by(
                models.VotingSession.date.desc(),
                models.VotingSession.cdeppk.desc(),
            ))
    return flask.render_template('votes/index.html', **{
        'voting_sessions': iter(voting_sessions),
    })


@votes.route('/votes/<uuid:voting_session_id>')
def detail(voting_session_id):
    voting_session = models.VotingSession.query.get_or_404(voting_session_id)
    votes = (
        voting_session.votes
            .join(models.Vote.mandate)
            .join(models.Mandate.person)
            .join(models.Mandate.county)
            .join(models.Mandate.group_memberships)
            .join(models.MpGroupMembership.mp_group))
    return flask.render_template('votes/detail.html', **{
        'voting_session': voting_session,
        'proposal': voting_session.proposal,
        'votes': iter(votes),
    })


@job
def calculate_voting_session_loyalty(voting_session_id, commit=False):
    voting_session = models.VotingSession.query.get(voting_session_id)

    # make sure we're in the right legislature
    assert voting_session.date >= date(2012, 12, 19)

    indep_group = models.MpGroup.query.filter_by(short_name='Indep.').first()
    assert indep_group is not None

    voter_query = (
        models.db.session.query(
            models.Vote,
            models.MpGroup,
        )
        .join(models.Vote.mandate)
        .join(models.Mandate.group_memberships)
        .join(models.MpGroupMembership.mp_group)
        .filter(
            models.MpGroupMembership.interval.contains(
                voting_session.date,
            ),
        )
        .filter(
            models.Vote.voting_session == voting_session
        )
    )

    vote_map = defaultdict(lambda: defaultdict(list))

    for vote, group in voter_query:
        if group != indep_group:
            vote_map[group.id][vote.choice].append(vote)

    majority_votes = {}

    for group_id, votes_by_choice in vote_map.items():
        top = max(
            (len(votes), choice)
            for choice, votes
            in votes_by_choice.items()
            if choice != 'novote'
        )
        top_choice = top[1]
        majority_votes[group_id] = top_choice

        for choice, votes in votes_by_choice.items():
            loyal = bool(choice == top_choice)
            for vote in votes:
                vote.loyal = loyal

    meta_row = models.Meta.get_or_create(voting_session.id, 'majority_votes')
    meta_row.value = majority_votes

    if commit:
        models.db.session.commit()


@votes_manager.command
def loyalty():
    voting_session_query = (
        models.VotingSession.query
        .filter(models.VotingSession.subject != "Prezenţă")
        .order_by(models.VotingSession.date)
    )
    job_count = 0
    for voting_session in voting_session_query:
        calculate_voting_session_loyalty.delay(voting_session.id, commit=True)
        job_count += 1

    models.db.session.commit()
    logger.info("Enqueued %d jobs", job_count)
