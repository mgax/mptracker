from datetime import date
from collections import defaultdict
import logging
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from sqlalchemy import or_
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
        .join(models.MpGroupMembership.mp_group)
        .order_by(models.Person.name)
    )
    return flask.render_template('votes/detail.html', **{
        'voting_session': voting_session,
        'proposal': voting_session.proposal,
        'votes': iter(votes),
    })


@votes.route('/votes/controversy')
def controversy():
    return flask.render_template('votes/controversy.html', **{
        'controversy_list': models.Controversy.query.all(),
    })


@job
def calculate_voting_session_loyalty(voting_session_id):
    voting_session = models.VotingSession.query.get(voting_session_id)

    # make sure we're in the right legislature
    assert voting_session.date >= date(2012, 12, 19)

    indep_group = models.MpGroup.query.filter_by(short_name='Indep.').first()
    assert indep_group is not None

    voter_query = (
        models.db.session.query(
            models.Vote,
            models.MpGroup,
            models.CabinetMembership,
        )
        .join(models.Vote.mandate)
        .join(models.Mandate.group_memberships)
        .join(models.MpGroupMembership.mp_group)
        .filter(
            models.MpGroupMembership.interval.contains(
                voting_session.date,
            ),
        )
        .outerjoin(models.MpGroup.cabinet_memberships)
        .filter(
            or_(
                models.CabinetMembership.interval == None,
                models.CabinetMembership.interval.contains(
                    voting_session.date,
                ),
            )
        )
        .filter(
            models.Vote.voting_session == voting_session
        )
    )

    vote_map = defaultdict(lambda: defaultdict(list))

    for vote, group, cabinet_membership in voter_query:
        vote_map[group.id][vote.choice].append(vote)

        if cabinet_membership is not None:
            vote_map['_cabinet'][vote.choice].append(vote)

    group_vote_map = {
        gv.mp_group_id: gv for gv in
        models.GroupVote.query.filter_by(voting_session_id=voting_session.id)
    }

    def get_top_choice(votes_by_choice):
        top = max(
            (len(votes), choice)
            for choice, votes
            in votes_by_choice.items()
            if choice != 'novote'
        )
        return top[1]

    cabinet_top_choice = get_top_choice(vote_map.pop('_cabinet'))
    voting_session.cabinet_choice = cabinet_top_choice

    for mp_group_id, votes_by_choice in vote_map.items():
        top_choice = get_top_choice(votes_by_choice)

        group_vote = group_vote_map.get(mp_group_id)
        if group_vote is None:
            group_vote = models.GroupVote(
                mp_group_id=mp_group_id,
                voting_session=voting_session,
            )
        group_vote.choice = top_choice
        group_vote.loyal_to_cabinet = bool(top_choice == cabinet_top_choice)

        for choice, votes in votes_by_choice.items():
            loyal = bool(choice == top_choice)
            loyal_to_cabinet = bool(top_choice == cabinet_top_choice)
            for vote in votes:
                vote.loyal = loyal
                vote.loyal_to_cabinet = loyal_to_cabinet

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
        calculate_voting_session_loyalty.delay(voting_session.id)
        job_count += 1

    logger.info("Enqueued %d jobs", job_count)
