import flask
from mptracker import models

proposals = flask.Blueprint('proposals', __name__)


@proposals.route('/person/<person_id>/proposals')
def person_proposals(person_id):
    person = models.Person.query.get_or_404(person_id)
    return flask.render_template('person_proposals.html', **{
        'person': person,
        'proposals': list(person.proposals),
    })


@proposals.route('/proposals/<proposal_id>')
def proposal(proposal_id):
    proposal = models.Proposal.query.get_or_404(proposal_id)
    return flask.render_template('proposal.html', **{
        'proposal': proposal,
    })
