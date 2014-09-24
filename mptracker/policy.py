import re
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from sqlalchemy import func
from pyquery import PyQuery as pq
from path import path
from mptracker import models
from mptracker.common import url_args, fix_local_chars

COMMITTEE_URL_PREFIX = 'http://www.cdep.ro/pls/parlam/structura.co?'

policy_manager = Manager()


def iter_committees(proposal):
    for activity_item in flask.json.loads(proposal.activity or '[]'):
        html = pq(activity_item['html'])
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
                assert committee is not None, \
                    "No such committee: %r/%r" % (args['cam'], args['idc'])
                yield committee


def get_proposal_policy_domain(proposal):
    for committee in iter_committees(proposal):
        if committee.policy_domain is not None:
            return committee.policy_domain
    else:
        return None


@policy_manager.command
@job
def calculate_proposal(proposal_id):
    proposal = models.Proposal.query.get(proposal_id)
    proposal.policy_domain = get_proposal_policy_domain(proposal)
    models.db.session.commit()


@policy_manager.command
def calculate_all_proposals():
    proposal_query = (
        models.db.session.query(models.Proposal.id)
        .filter(models.Proposal.policy_domain_id == None)
    )
    for (proposal_id,) in proposal_query:
        calculate_proposal.delay(proposal_id)


@policy_manager.command
@job
def calculate_question(question_id):
    fixup_path = path(__file__).abspath().parent / 'ministry_name_fixup.json'
    with fixup_path.open('rb') as f:
        fixup_map = flask.json.loads(f.read().decode('utf-8'))

    question = models.Question.query.get(question_id)
    name = fix_local_chars(question.addressee)
    for name in name.split(';'):
        name = re.sub(r'\s+', ' ', name.strip()).lower()
        if name in fixup_map:
            name = fixup_map[name]
        ministry = (
            models.Ministry.query
            .filter(func.lower(models.Ministry.name) == name.lower())
            .first()
        )
        if ministry is not None:
            break
    else:
        return

    question.policy_domain_id = ministry.policy_domain_id
    models.db.session.commit()



@policy_manager.command
def calculate_all_questions():
    question_query = (
        models.db.session.query(models.Question.id)
        .filter(models.Question.date >= '2012-12-19')
        .filter(models.Question.policy_domain_id == None)
    )
    for (question_id,) in question_query:
        calculate_question.delay(question_id)
