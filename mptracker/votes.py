import flask
from mptracker import models


votes = flask.Blueprint('votes', __name__)


@votes.route('/votes/')
def index():
    voting_sessions = (
        models.VotingSession.query
            .order_by(models.VotingSession.cdeppk.desc()))
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
