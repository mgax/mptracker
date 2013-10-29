from datetime import date
from collections import defaultdict
import flask
from flask.ext.script import Manager
from sqlalchemy import func
from mptracker import models


loyalty_manager = Manager()


@loyalty_manager.command
def calculate_groups():
    voting_session_query = (
        models.VotingSession.query
        .filter(models.VotingSession.subject != "Prezenţă")
        .order_by(models.VotingSession.date)
    )
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
            .filter(
                models.MpGroupMembership.interval.contains(
                    voting_session.date,
                ),
            )
            .join(models.MpGroupMembership.mp_group)
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

        from pprint import pprint
        pprint(dict(groups))
        break
