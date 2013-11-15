import flask
from flask.ext.script import Manager
from pyquery import PyQuery as pq
from mptracker import models
from mptracker.common import url_args

COMMITTEE_URL_PREFIX = 'http://www.cdep.ro/pls/parlam/structura.co?'

policy_manager = Manager()


def iter_committees(proposal):
    for activity_item in proposal.activity:
        html = pq(activity_item.html)
        for link in html.items('a'):
            href = link.attr('href')
            if href and href.startswith(COMMITTEE_URL_PREFIX):
                args = url_args(href)
                committee = (
                    models.MpCommittee.query
                    .filter_by(chamber_id=int(args['cam']))
                    .filter_by(cdep_id=int(args['idc']))
                    .first()
                )
                assert committee is not None
                yield committee


@policy_manager.command
def calculate_proposal(proposal_id):
    proposal = models.Proposal.query.get(proposal_id)

    for committee in iter_committees(proposal):
        print(committee.name)
