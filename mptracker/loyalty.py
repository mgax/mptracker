from datetime import date
from collections import defaultdict
import logging
import flask
from flask.ext.script import Manager
from sqlalchemy import func
from mptracker import models

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

loyalty_manager = Manager()


@loyalty_manager.command
def calculate_groups():
    voting_session_query = (
        models.VotingSession.query
        .filter(models.VotingSession.subject != "Prezenţă")
        .order_by(models.VotingSession.date)
    )
    session_count = 0
    for voting_session in voting_session_query:
        # make sure we're in the right legislature
        assert voting_session.date >= date(2012, 12, 19)

        vote_query = (
            models.db.session.query(
                models.MpGroup.id,
                models.Vote.choice,
                func.count('*'),
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
            .group_by(
                models.MpGroup.id,
                models.Vote.choice,
            )
        )

        groups = defaultdict(dict)
        for group_id, choice, count in vote_query:
            groups[group_id][choice] = count

        def majority(group_votes):
            return max((n, choice) for choice, n in group_votes.items())[1]

        meta_row = models.Meta.get_or_create(voting_session.id, 'group_votes')
        meta_row.value = {
            group_id: majority(votes)
            for group_id, votes in groups.items()
        }

        session_count += 1

    models.db.session.commit()
    logger.info("Calculated majority for %d voting sessions", session_count)
