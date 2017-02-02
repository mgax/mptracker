from datetime import date
from collections import defaultdict
from itertools import groupby
from sqlalchemy import func, distinct, and_
from sqlalchemy.orm import joinedload, aliased
from flask import json
from mptracker.common import PARTY_ORDER
from mptracker.models import (
    Ask,
    Chamber,
    County,
    GroupVote,
    Mandate,
    Match,
    MpCommittee,
    MpCommitteeMembership,
    MpGroup,
    MpGroupMembership,
    NameSearch,
    Person,
    PolicyDomain,
    Proposal,
    ProposalControversy,
    Question,
    Sponsorship,
    Transcript,
    TranscriptChapter,
    Vote,
    VotingSession,
    VotingSessionControversy,
    db,
)
from mptracker.website.dal_common import (
    pluck_tacit_approval,
    _get_recent_questions,
    _get_recent_proposals,
    TACIT_APPROVAL_SUBSTRING,
    read_activity_item,
    LEGISLATURE_2016_START,
)
from mptracker.website.dal_person import DalPerson
from mptracker.website.dal_party import DalParty


class DalCounty:

    def __init__(self, county_code, missing=KeyError):
        self.county = County.query.filter_by(code=county_code).first()
        if self.county is None:
            raise missing()

    def get_details(self):
        return {
            'name': self.county.name,
        }

    def get_mandates_data(self):
        query = (
            Mandate.query
            .filter_by(year=2016)
            .filter_by(county=self.county)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .options(joinedload('person'))
            .order_by(Mandate.college, Mandate.election_votes.desc())
        )
        return [
            {
                'college': m.college,
                'person_name': m.person.name_first_last,
                'person_slug': m.person.slug,
            }
            for m in query
        ]


class DataAccess:

    def __init__(self, missing=KeyError):
        self.missing = missing

    def get_county_name_map(self):
        return {c.code: c.name for c in County.query}

    def get_2016_mandates_by_county(self):
        mandates = (
            Mandate.query
            .filter_by(year=2016)
            .join(Mandate.person)
            .join(Mandate.county)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
        )

        mandate_data = defaultdict(list)
        for m in mandates:
            #key = '%s%d' % (m.county.code, m.college)
            key = m.county.code
            mandate_data[key].append({
                'name': m.person.name_first_last,
                'person_slug': m.person.slug,
            })

        return dict(mandate_data)

    def search_person_by_name(self, name_query):
        name_search = NameSearch(
            Person.query
            .join(Person.mandates)
            .filter_by(year=2016)
            .order_by(Person.first_name, Person.last_name)
        )
        return [
            {'name': person.name_first_last, 'slug': person.slug}
            for person in name_search.find(name_query.strip())
        ]

    def search_person_by_policy(self, policy_slug):
        policy_domain = (
            PolicyDomain.query
            .filter_by(slug=policy_slug)
            .first()
        )
        if policy_domain is None:
            return []

        proposals_cte = (
            db.session.query(
                Sponsorship.mandate_id,
                func.count('*').label('proposal_count')
            )
            .join(Sponsorship.proposal)
            .filter_by(policy_domain=policy_domain)
            .group_by(Sponsorship.mandate_id)
            .cte()
        )

        questions_cte = (
            db.session.query(
                Ask.mandate_id,
                func.count('*').label('question_count')
            )
            .join(Ask.question)
            .filter_by(policy_domain=policy_domain)
            .group_by(Ask.mandate_id)
            .cte()
        )

        activity_query = (
            db.session.query(
                Person,
                proposals_cte.c.proposal_count,
                questions_cte.c.question_count,
            )
            .join(Mandate.person)
            .filter(Mandate.year == 2016)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .outerjoin(proposals_cte, proposals_cte.c.mandate_id == Mandate.id)
            .outerjoin(questions_cte, questions_cte.c.mandate_id == Mandate.id)
        )

        rv = [
            {
                'name': person.name_first_last,
                'slug': person.slug,
                'count': (proposal_count or 0) + (question_count or 0),
            }
            for person, proposal_count, question_count in activity_query
        ]
        rv.sort(key=lambda r: r['count'], reverse=True)

        return [r for r in rv if r['count'] > 0]

    def search_person_by_contracts(self, contracts_query):
        person_query = (
            Person.query
            .join(Mandate.person)
            .filter(Mandate.year == 2016)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .filter(Person.romania_curata != '')
            .filter(Person.romania_curata != None)
        )
        if contracts_query:
            person_query = (
                person_query
                .filter(
                    "to_tsvector('romanian', person.romania_curata) "
                    "@@ plainto_tsquery('romanian', :contracts_query)"
                )
                .params(contracts_query=contracts_query)
            )

        return [
            {'name': person.name_first_last, 'slug': person.slug}
            for person in person_query
        ]

    def get_person(self, person_slug):
        return DalPerson(person_slug, self, self.missing)

    def get_county(self, county_code):
        return DalCounty(county_code, self.missing)

    def get_recent_proposals(self, limit):
        return _get_recent_proposals(None, limit)

    def get_recent_questions(self, limit):
        return _get_recent_questions(None, limit)

    def get_tacit_approvals_count(self):
        return self.get_policy_tacit_approval_qs().count()

    def get_controversy_count(self):
        return ProposalControversy.query.count()

    def get_question_details(self, question_id):
        question = Question.query.get(question_id)
        if question is None:
            raise self.missing()

        rv = {'title': question.title}

        asked_query = (
            Person.query
            .join(Person.mandates)
            .join(Mandate.asked)
            .filter(Ask.question == question)
        )
        rv['asked_by'] = []
        for person in asked_query:
            rv['asked_by'].append({
                'name': person.name_first_last,
                'slug': person.slug,
            })

        if question.pdf_url:
            rv['question_pdf_url'] = question.pdf_url

        if question.answer and question.answer.pdf_url:
            rv['answer_pdf_url'] = question.answer.pdf_url

        return rv

    def get_party_qs(self, year=2016):
        return (
            MpGroup.query
            .filter_by(year=year)
            .order_by(MpGroup.name)
        )

    def get_parties(self):
        return [
            DalParty(self, p.short_name, missing=self.missing)
            for p in self.get_party_qs()
        ]

    def get_party(self, party_short_name):
        return DalParty(self, party_short_name, missing=self.missing)

    def get_group_membership(self, day):
        query = (
            db.session.query(
                MpGroupMembership,
                MpGroup,
                Person,
            )
            .join(MpGroupMembership.mp_group)
            .join(MpGroupMembership.mandate)
            .join(Mandate.person)
            .filter(MpGroupMembership.interval.contains(day))
            .order_by(
                func.lower(MpGroupMembership.interval),
                Person.first_name,
                Person.last_name,
            )
        )
        null_end = lambda d: None if d.year == 9999 else d
        for (membership, group, person) in query:
            yield {
                'name': person.name_first_last,
                'group': group.name,
                'start': membership.interval.lower,
                'end': null_end(membership.interval.upper),
            }

    def get_group_migrations(self, start, end):
        query = (
            db.session.query(
                MpGroupMembership,
                Mandate,
                Person,
            )
            .join(MpGroupMembership.mandate)
            .join(Mandate.person)
            .filter(Mandate.year == 2016)
            .order_by(
                Person.last_name,
                Person.first_name,
                Mandate.id,
                func.lower(MpGroupMembership.interval),
            )
        )

        for mandate, membership_iter in groupby(query, lambda r: r.Mandate):
            prev = None
            for (membership, _, person) in membership_iter:
                if prev:
                    day = prev.interval.upper
                    assert membership.interval.lower == day
                    yield {
                        'name': person.name_first_last,
                        'date': day,
                        'group_old': prev.mp_group.name,
                        'group_new': membership.mp_group.name,
                    }

                if start <= membership.interval.upper < end:
                    prev = membership
                else:
                    prev = None

    def get_bounded_mandates(self, request):
        query = (
            db.session.query(
                MpGroupMembership,
                MpGroup,
                Person,
            )
            .join(MpGroupMembership.mp_group)
            .join(MpGroupMembership.mandate)
            .join(Mandate.person)
            .filter(Mandate.year == 2016)
            .order_by(
                func.lower(MpGroupMembership.interval),
                Person.first_name,
                Person.last_name,
            )
        )

        if request == 'late_start':
            query = (
                query
                .filter(func.lower(MpGroupMembership.interval) ==
                        func.lower(Mandate.interval))
                .filter(func.lower(Mandate.interval) > date(2016, 12, 21))
            )

        elif request == 'early_end':
            query = (
                query
                .filter(func.upper(MpGroupMembership.interval) ==
                        func.upper(Mandate.interval)
                )
                .filter(func.upper(Mandate.interval) < date.today())
            )

        else:
            raise RuntimeError("Unknown request %r" % request)

        for (membership, group, person) in query:
            yv = {
                'name': person.name_first_last,
                'group': group.name,
                'start': membership.interval.lower,
                'end': membership.interval.upper,
            }

            yield yv

    def get_party_list(self):
        mp_group_query = self.get_party_qs()
        return [
            {'name': group.name, 'short_name': group.short_name}
            for group in mp_group_query
            if group.short_name not in ['Indep.']
        ]

    def get_policy_list(self):
        return [
            {'name': policy.name, 'slug': policy.slug}
            for policy in PolicyDomain.query.order_by(PolicyDomain.name.asc())
        ]

    def get_policy(self, policy_slug):
        policy = PolicyDomain.query.filter_by(slug=policy_slug).first()
        if policy is None:
            raise self.missing()
        return {'name': policy.name}

    def get_policy_tacit_approval_qs(self):
        return (
            Proposal.query
            .filter(Proposal.date >= LEGISLATURE_2016_START)
            .filter(
                Proposal.activity.like('%' + TACIT_APPROVAL_SUBSTRING + '%')
            )
        )

    def get_policy_proposal_list(self,
            policy_slug=None, mandate=None, party=None, limit=None):
        proposal_query = (
            db.session.query(
                distinct(Proposal.id)
            )
            .filter(Proposal.date >= LEGISLATURE_2016_START)
            .outerjoin(Proposal.policy_domain)
        )

        if policy_slug:
            proposal_query = proposal_query.filter_by(slug=policy_slug)

        if mandate is not None:
            proposal_query = (
                proposal_query
                .join(Proposal.sponsorships)
                .filter_by(mandate=mandate)
            )

        elif party is not None:
            proposal_query = (
                proposal_query
                .join(Proposal.sponsorships)
                .join(Sponsorship.mandate)
                .join(Mandate.group_memberships)
                .filter(MpGroupMembership.mp_group == party)
                .filter(MpGroupMembership.interval.contains(Proposal.date))
            )

        query = (
            Proposal.query
            .filter(Proposal.id.in_([r[0] for r in proposal_query]))
            .order_by(Proposal.modification_date.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return [
            {
                'title': proposal.title,
                'date': proposal.date,
                'modification_date': proposal.modification_date,
                'id': proposal.id,
                'status': proposal.status,
                'tacit_approval': pluck_tacit_approval(proposal),
                'controversy': proposal.controversy.all(),
                'cdeppk_cdep': proposal.cdeppk_cdep,
                'cdeppk_senate': proposal.cdeppk_senate,
            }
            for proposal in query
        ]

    def get_policy_tacit_approval_list(self, limit=None):
        qs = (
            self.get_policy_tacit_approval_qs()
            .order_by(Proposal.modification_date.desc())
        )
        if limit:
            qs = qs.limit(limit)
        return [
            {
                'title': proposal.title,
                'id': proposal.id,
                'status': proposal.status,
                'tacit_approval': pluck_tacit_approval(proposal),
                'controversy': proposal.controversy.all(),
                'date': proposal.date,
                'modification_date': proposal.modification_date,
            }
            for proposal in qs
        ]

    def get_policy_tacit_approval_count(self):
        return self.get_policy_tacit_approval_qs().count()

    def get_policy_controversy_list(self, limit=None):
        qs = (
            db.session.query(
                ProposalControversy,
                Proposal,
            )
            .join(ProposalControversy.proposal)
            .order_by(Proposal.modification_date.desc())
        )
        if limit:
            qs = qs.limit(limit)

        return [
            {
                'title': controversy.title,
                'id': proposal.id,
                'status': proposal.status,
                'tacit_approval': pluck_tacit_approval(proposal),
                'controversy': proposal.controversy.all(),
                'date': proposal.date,
                'modification_date': proposal.modification_date,
            }
            for (controversy, proposal) in qs
        ]

    def get_policy_controversy_count(self):
        return ProposalControversy.query.count()

    def get_policy_question_list(self, policy_slug=None, mandate=None, party=None):
        question_query = (
            db.session.query(
                distinct(Question.id),
            )
            .outerjoin(Question.policy_domain)
            .filter(Question.date >= LEGISLATURE_2016_START)
        )

        if policy_slug:
            question_query = question_query.filter_by(slug=policy_slug)

        if mandate is not None:
            question_query = (
                question_query
                .join(Question.asked)
                .filter_by(mandate=mandate)
            )

        elif party is not None:
            question_query = (
                question_query
                .join(Question.asked)
                .join(Ask.mandate)
                .join(Mandate.group_memberships)
                .filter(MpGroupMembership.mp_group == party)
                .filter(MpGroupMembership.interval.contains(Question.date))
            )

        return [
            {
                'title': question.title,
                'id': question.id,
                'date': question.date,
                'type': question.type,
            }
            for question in (
                Question.query
                .filter(Question.id.in_([r[0] for r in question_query]))
                .order_by(Question.date.desc())
            )
        ]

    def get_policy_top_parties(self, policy_slug, cutoff=0.05):
        count_map = defaultdict(int)

        question_query = (
            db.session.query(
                MpGroupMembership.mp_group_id,
                func.count(distinct(Question.id)),
            )
            .select_from(Question)
            .join(Question.asked)
            .join(Ask.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.interval.contains(Question.date))
            .join(Question.policy_domain)
            .filter(PolicyDomain.slug == policy_slug)
            .join(MpGroupMembership.mp_group)
            .filter(MpGroup.year == 2016)
            .group_by(MpGroupMembership.mp_group_id)
        )

        for mp_group_id, count in question_query:
            count_map[mp_group_id] += count

        proposal_query = (
            db.session.query(
                MpGroupMembership.mp_group_id,
                func.count(distinct(Proposal.id))
            )
            .select_from(Proposal)
            .filter(Proposal.date >= LEGISLATURE_2016_START)
            .join(Proposal.sponsorships)
            .join(Sponsorship.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.interval.contains(Proposal.date))
            .join(Proposal.policy_domain)
            .filter(PolicyDomain.slug == policy_slug)
            .join(MpGroupMembership.mp_group)
            .filter(MpGroup.year == 2016)
            .group_by(MpGroupMembership.mp_group_id)
        )

        for mp_group_id, count in proposal_query:
            count_map[mp_group_id] += count

        total = sum(count_map.values())

        group_list = []
        if total:
            for party in MpGroup.query:
                interest = count_map.get(party.id, 0) / total
                if interest > cutoff:
                    group_list.append({
                        'short_name': party.short_name,
                        'name': party.name,
                        'interest': interest,
                    })

        return sorted(
            group_list,
            reverse=True,
            key=lambda p: p['interest'],
        )

    def get_proposal_details(self, proposal_id):
        proposal = Proposal.query.get(proposal_id)
        if proposal is None:
            raise self.missing()

        activity = [
            read_activity_item(item)
            for item in reversed(json.loads(proposal.activity or '[]'))
        ]

        rv = {
            'title': proposal.title,
            'controversy': proposal.controversy.all(),
            'pk_cdep': proposal.cdeppk_cdep,
            'pk_senate': proposal.cdeppk_senate,
            'activity': activity,
        }

        sponsors_query = (
            Person.query
            .join(Person.mandates)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(Mandate.sponsorships)
            .filter(Sponsorship.proposal == proposal)
        )
        rv['sponsors'] = []
        for person in sponsors_query:
            rv['sponsors'].append({
                'name': person.name_first_last,
                'slug': person.slug,
            })

        return rv

    def get_transcript_chapter(self, serial):
        transcript_chapter = (
            TranscriptChapter.query
            .filter_by(serial=serial)
            .first()
        )
        if transcript_chapter is None:
            raise self.missing()

        rv = {
            'serial': transcript_chapter.serial,
            'date': transcript_chapter.date,
            'headline': transcript_chapter.headline,
        }

        transcript_query = (
            db.session.query(
                Transcript,
                Person,
            )
            .filter_by(chapter=transcript_chapter)
            .join(Transcript.mandate)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(Mandate.person)
            .order_by(Transcript.serial)
        )
        rv['transcript_list'] = [
            {
                'text': transcript.text,
                'person_name': person.name_first_last,
                'person_slug': person.slug,
                'serial_id': transcript.serial_id,
            }
            for transcript, person in transcript_query
        ]
        return rv

    def get_transcript(self, serial):
        transcript = (
            Transcript.query
            .filter_by(serial=serial)
            .first()
        )
        if transcript is None:
            raise self.missing()

        return {
            'date': transcript.chapter.date,
            'text': transcript.text,
        }

    def get_all_votes(self, year):
        vote_query = (
            db.session.query(
                Vote.choice,
                Person.first_name,
                Person.last_name,
                GroupVote.choice.label('group_choice'),
                VotingSession.date,
                VotingSession.cdeppk,
            )
            .join(Vote.voting_session)
            .filter_by(final=True)
            .join(VotingSession.group_votes)
            .join(Vote.mandate)
            .filter_by(year=2016)
            .join(Mandate.person)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group_id == GroupVote.mp_group_id)
            .filter(MpGroupMembership.interval.contains(VotingSession.date))
            .order_by(VotingSession.date, VotingSession.cdeppk)
        )

        if year is not None:
            vote_query = (
                vote_query
                .filter(VotingSession.date >= date(year, 1, 1))
                .filter(VotingSession.date < date(year+1, 1, 1))
            )

        for row in vote_query.yield_per(10):
            yield {
                'name': "{row.first_name} {row.last_name}".format(row=row),
                'choice': row.choice,
                'group_choice': row.group_choice,
                'cdeppk': row.cdeppk,
                'date': row.date,
            }

    def get_all_questions(self, year):
        question_query = (
            db.session.query(
                Question,
                Person,
                Match.score,
            )
            .join(Question.asked)
            .join(Ask.mandate)
            .filter_by(year=2016)
            .join(Mandate.person)
            .join(Ask.match_row)
            .order_by(Question.date, Question.number)
        )

        if year is not None:
            question_query = (
                question_query
                .filter(Question.date >= date(year, 1, 1))
                .filter(Question.date < date(year+1, 1, 1))
            )

        for (question, person, local_score) in question_query:
            yield {
                'name': person.name_first_last,
                'number': question.number,
                'date': question.date,
                'type': question.type,
                'title': question.title,
                'addressee': question.addressee,
                'local_score': local_score,
            }

    def _get_migrations_query(self, limit):
        OldGroup = aliased(MpGroup)
        NewGroup = aliased(MpGroup)
        OldMembership = aliased(MpGroupMembership)
        NewMembership = aliased(MpGroupMembership)
        OtherMembership = aliased(MpGroupMembership)

        migrations_cte = (
            db.session.query(
                MpGroupMembership.id.label('membership_id'),
                MpGroupMembership.interval,
                Person.id.label('person_id'),
            )
            .join(MpGroupMembership.mandate)
            .filter_by(year=2016)
            .join(Mandate.person)
            .order_by(MpGroupMembership.interval.desc())
            .limit(limit)
            .cte()
        )

        return (
            db.session.query(
                Person,
                migrations_cte.c.interval,
                OldGroup,
                NewGroup,
            )
            .join(migrations_cte,
                migrations_cte.c.person_id == Person.id,
            )
            .join(NewMembership,
                NewMembership.id == migrations_cte.c.membership_id,
            )
            .join(NewGroup,
                NewGroup.id == NewMembership.mp_group_id,
            )
            .join(OldMembership,
                OldMembership.mandate_id == NewMembership.mandate_id,
            )
            .join(OldGroup,
                OldGroup.id == OldMembership.mp_group_id,
            )
            .outerjoin(OtherMembership,
                and_(
                    OtherMembership.mandate_id == NewMembership.mandate_id,
                    OtherMembership.interval > OldMembership.interval,
                    OtherMembership.interval < NewMembership.interval,
                )
            )
            .filter(OldMembership.interval < NewMembership.interval)
            .filter(OtherMembership.id == None)
            .order_by(NewMembership.interval.desc())
        )

    def get_migrations(self, limit=None):
        migrations_query = self._get_migrations_query(limit)
        for (person, interval, old_group, new_group) in migrations_query:
            yield {
                'person': {
                    'name': person.name_first_last,
                    'slug': person.slug,
                },
                'old_group': {
                    'short_name': old_group.short_name,
                },
                'new_group': {
                    'short_name': new_group.short_name,
                },
                'date': interval.lower,
            }

    def get_migration_count(self):
        return self._get_migrations_query(limit=None).count()

    def get_vote_controversy(self, controversy_id):
        controversy = VotingSessionControversy.query.get(controversy_id)
        if controversy is None:
            raise self.missing()

        return {
            'title': controversy.title,
            'date': controversy.voting_session.date,
            'cdeppk': controversy.voting_session.cdeppk,
            'reason': controversy.reason,
            'meaning_yes': controversy.vote_meaning_yes,
            'meaning_no': controversy.vote_meaning_no,
            'press_link_list': controversy.press_links.split(),
        }

    def get_top_policies(self):
        count_map = defaultdict(int)

        question_query = (
            db.session.query(
                PolicyDomain.id,
                func.count('*'),
            )
            .select_from(Question)
            .join(Question.asked)
            .join(Ask.mandate)
            .filter_by(year=2016)
            .join(Question.policy_domain)
            .group_by(PolicyDomain.id)
        )
        for policy_domain_id, count in question_query:
            count_map[policy_domain_id] += count

        proposal_query = (
            db.session.query(
                PolicyDomain.id,
                func.count('*'),
            )
            .select_from(Proposal)
            .filter(Proposal.date >= LEGISLATURE_2016_START)
            .join(Proposal.sponsorships)
            .join(Sponsorship.mandate)
            .filter_by(year=2016)
            .join(Proposal.policy_domain)
            .group_by(PolicyDomain.id)
        )
        for policy_domain_id, count in proposal_query:
            count_map[policy_domain_id] += count

        total = sum(count_map.values())

        policy_list = []
        if total:
            for policy_domain in PolicyDomain.query:
                interest = count_map.get(policy_domain.id, 0) / total
                policy_list.append({
                    'slug': policy_domain.slug,
                    'name': policy_domain.name,
                    'interest': interest,
                })

        return sorted(
            policy_list,
            reverse=True,
            key=lambda p: p['interest'],
        )

    def get_seats(self):
        by_party = dict(
            db.session.query(
                MpGroup.short_name,
                func.count(MpGroupMembership.id),
            )
            .join(MpGroupMembership.mp_group)
            .filter(MpGroup.year == 2016)
            .filter(func.upper(MpGroupMembership.interval) == 'infinity')
            .group_by(MpGroup.short_name)
            .all()
        )

        offset = 0
        rv = []

        for short_name in PARTY_ORDER:
            count = by_party.get(short_name, 0)
            rv.append({
                'party': short_name,
                'count': count,
                'offset': offset,
            })
            offset += count

        return rv

    def get_policy_committees(self, slug):
        if slug is None:
            return []
        policy = PolicyDomain.query.filter_by(slug=slug).one()
        return [
            {
                'name': committee.name,
                'id': committee.id,
                'chamber': committee.chamber_id,
            }
            for committee in policy.committees.order_by('-chamber_id', 'name')
        ]

    def get_committee_details(self, committee_id):
        committee = MpCommittee.query.get(committee_id)
        if committee is None:
            raise self.missing()

        person_query = (
            db.session.query(
                Person,
                MpCommitteeMembership,
            )
            .join(Person.mandates)
            .join(Mandate.committee_memberships)
            .filter(MpCommitteeMembership.mp_committee == committee)
            .filter(MpCommitteeMembership.interval.contains(date.today()))
            .order_by(Person.slug)
        )

        member_list = [
            {
                'slug': person.slug,
                'name': person.name_first_last,
                'role': membership.role,
            }
            for (person, membership) in person_query
        ]

        return {
            'name': committee.name,
            'chamber_id': committee.chamber_id,
            'cdep_id': committee.cdep_id,
            'member_list': member_list,
        }

    def get_all_proposals(self, year):
        sponsors_cte = lambda chamber_slug: (
            db.session.query(
                Sponsorship.proposal_id.label('id'),
                func.string_agg(
                    Person.first_name + " " + Person.last_name,
                    ', '
                ).label('namelist'),
            )
            .join(Sponsorship.mandate)
            .join(Mandate.person)
            .join(Mandate.chamber)
            .filter(Chamber.slug == chamber_slug)
            .group_by(Sponsorship.proposal_id)
            .cte()
        )

        cdep_cte = sponsors_cte('cdep')
        senate_cte = sponsors_cte('senat')

        query = (
            db.session.query(
                Proposal,
                cdep_cte.c.namelist,
                senate_cte.c.namelist,
            )
            .outerjoin(cdep_cte, cdep_cte.c.id == Proposal.id)
            .outerjoin(senate_cte, senate_cte.c.id == Proposal.id)
            .filter(Proposal.date >= date(year, 1, 1))
            .filter(Proposal.date <= date(year, 12, 31))
            .order_by(Proposal.date, Proposal.id)
        )

        for (proposal, namelist_cdep, namelist_senate) in query:
            yield {
                'title': proposal.title,
                'url_cdep': proposal.url_cdep,
                'url_senate': proposal.url_senate,
                'number_cdep': proposal.number_cdep,
                'number_senate': proposal.number_senate,
                'number_bpi': proposal.number_bpi,
                'date': proposal.date,
                'modification_date': proposal.modification_date,
                'status': proposal.status,
                'namelist_cdep': namelist_cdep or "",
                'namelist_senate': namelist_senate or "",
            }

    def get_mandate_activity(self, year):
        proposal_cte = (
            db.session.query(
                Mandate.id,
                func.count(Proposal.id)
                    .label('total'),
                func.count(func.nullif(Proposal.status, 'inprogress'))
                    .label('_inprogress'),
                func.count(func.nullif(Proposal.status, 'approved'))
                    .label('_approved'),
                func.count(func.nullif(Proposal.status, 'rejected'))
                    .label('_rejected'),
            )
            .join(Sponsorship.mandate)
            .join(Sponsorship.proposal)
            .filter(Proposal.date >= date(year, 1, 1))
            .filter(Proposal.date <= date(year, 12, 31))
            .group_by(Mandate.id)
            .cte()
        )

        transcript_cte = (
            db.session.query(
                Mandate.id,
                func.count(Transcript.id).label('transcripts'),
            )
            .join(Mandate.transcripts)
            .join(Transcript.chapter)
            .filter(TranscriptChapter.date >= date(year, 1, 1))
            .filter(TranscriptChapter.date <= date(year, 12, 31))
            .group_by(Mandate.id)
            .cte()
        )

        questions_cte = (
            db.session.query(
                Mandate.id,
                func.count('*').label('questions'),
                func.count(func.nullif(Match.score, 0)).label('qlocal'),
            )
            .join(Mandate.asked)
            .join(Ask.question)
            .filter(Question.date >= date(year, 1, 1))
            .filter(Question.date <= date(year, 12, 31))
            .join(Ask.match_row)
            .group_by(Mandate.id)
            .cte()
        )

        query = (
            db.session.query(
                Person,
                proposal_cte.c.total,
                proposal_cte.c._inprogress,
                proposal_cte.c._approved,
                proposal_cte.c._rejected,
                transcript_cte.c.transcripts,
                questions_cte.c.questions,
                questions_cte.c.qlocal,
            )
            .join(Mandate.person)
            .filter(Mandate.year == 2016)
            .outerjoin(proposal_cte, Mandate.id == proposal_cte.c.id)
            .outerjoin(transcript_cte, Mandate.id == transcript_cte.c.id)
            .outerjoin(questions_cte, Mandate.id == questions_cte.c.id)
            .order_by(Person.first_name, Person.last_name, Person.id)
        )

        for (person, total, _inprogress, _approved, _rejected,
             transcripts, questions, qlocal) in query:
            yield {
                'name': person.name_first_last,
                'proposals_total': (total or 0),
                'proposals_inprogress': (total or 0) - (_inprogress or 0),
                'proposals_approved': (total or 0) - (_approved or 0),
                'proposals_rejected': (total or 0) - (_rejected or 0),
                'transcripts': transcripts or 0,
                'questions': questions or 0,
                'questions-local': qlocal or 0,
            }
