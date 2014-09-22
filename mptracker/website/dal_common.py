from datetime import date
from jinja2 import filters
from flask import json
from mptracker.common import parse_date
from mptracker.models import (
    Ask,
    Proposal,
    Question,
    Sponsorship,
)

LEGISLATURE_2012_START = date(2012, 12, 17)
TACIT_APPROVAL_SUBSTRING = 'art.75'


def read_activity_item(item):
    return {
        'date': parse_date(item['date']),
        'location': item['location'].lower(),
        'html': item['html'],
    }


def pluck_tacit_approval(proposal):
    for item in json.loads(proposal.activity or '[]'):
        if TACIT_APPROVAL_SUBSTRING in item['html']:
            return read_activity_item(item)

    else:
        return None


def _get_recent_questions(mandate, limit):
    recent_questions_query = (
        Question.query
        .order_by(Question.date.desc())
    )

    if mandate is not None:
        recent_questions_query = (
            recent_questions_query
            .join(Question.asked)
            .filter(Ask.mandate == mandate)
        )

    if limit is not None:
        recent_questions_query = recent_questions_query.limit(limit)

    return [
        {
            'date': q.date,
            'text': filters.do_truncate(q.title),
            'type': q.type,
            'question_id': q.id,
        }
        for q in recent_questions_query
    ]


def _get_recent_proposals(mandate, limit):
    recent_proposals_query = (
        Proposal.query
        .order_by(Proposal.date.desc())
    )

    if mandate is not None:
        recent_proposals_query = (
            recent_proposals_query
            .join(Proposal.sponsorships)
            .filter(Sponsorship.mandate == mandate)
        )

    if limit is not None:
        recent_proposals_query = recent_proposals_query.limit(limit)

    return [
        {
            'date': p.date,
            'text': p.title,
            'type': 'proposal',
            'proposal_id': p.id,
        }
        for p in recent_proposals_query
    ]
