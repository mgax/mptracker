from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy import func, distinct, and_, desc
from sqlalchemy.orm import joinedload, aliased
from jinja2 import filters
from flask import json
from mptracker.common import parse_date
from mptracker.models import (
    Chamber,
    County,
    Person,
    Mandate,
    MpGroup,
    MpGroupMembership,
    MpCommittee,
    MpCommitteeMembership,
    Proposal,
    Sponsorship,
    TranscriptChapter,
    Transcript,
    Question,
    Ask,
    Match,
    VotingSession,
    VotingSessionControversy,
    Vote,
    GroupVote,
    PolicyDomain,
    Position,
    NameSearch,
    db,
    ProposalControversy,
    MemberCount,
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


def group_by_week(data_iter):
    rv = defaultdict(int)
    for day, value in data_iter:
        monday = day - timedelta(days=day.weekday())
        rv[monday] += value
    return dict(rv)


class DalPerson:

    def __init__(self, person_slug, dal, missing=KeyError):
        self.dal = dal

        self.person = Person.query.filter_by(slug=person_slug).first()
        if self.person is None:
            raise missing()

        self.mandate = (
            Mandate.query
            .filter_by(person=self.person)
            .filter_by(year=2012)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .first()
        )
        if self.mandate is None:
            raise missing()

    def get_main_details(self):
        return {
            'name': self.person.name_first_last,
            'person_id': self.person.id,
            'person_slug': self.person.slug,
            'mandate_id': self.mandate.id,
        }

    @property
    def picture_filename(self):
        return '%s.jpg' % str(self.person.slug)

    @property
    def _local_ask_query(self):
        return (
            self.mandate.asked
            .join(Ask.match_row)
            .filter(Match.score > 0)
        )

    @property
    def _local_sponsorship_query(self):
        return (
            self.mandate.sponsorships
            .join(Sponsorship.match_row)
            .filter(Match.score > 0)
        )

    def get_details(self):
        rv = self.get_main_details()
        rv.update({
            'romania_curata_text': self.person.romania_curata,
            'position_list': [
                {
                    'title': p.title,
                    'start_date': p.interval.lower,
                    'end_date': p.interval.upper,
                    'url': p.url,
                }
                for p in self.person.positions
            ],
            'mandate_count': self.person.mandates.count(),
        })

        committee_membership_query = (
            self.mandate.committee_memberships
            .options(joinedload('mp_committee'))
            .order_by(MpCommitteeMembership.interval.desc())
        )
        rv['committee_list'] = [

            {
                'start_date': cm.interval.lower,
                'end_date': cm.interval.upper,
                'role': cm.role,
                'committee_name': cm.mp_committee.name,
                'committee_url': cm.mp_committee.cdep_url,
                'attendance_2013': cm.attendance_2013,
            }
            for cm in committee_membership_query
        ]

        if self.mandate.county:
            votes_percent = self.mandate.election_votes_percent
            rv['college'] = {
                'county_name': self.mandate.county.name,
                'county_code': self.mandate.county.code,
                'number': self.mandate.college,
                'election_votes_fraction': votes_percent and votes_percent/100,
            }

        vote_subquery = Vote.query.filter_by(mandate=self.mandate).subquery()
        controversy_query = (
            db.session.query(
                VotingSessionControversy,
                VotingSession.date,
                vote_subquery.c.choice,
            )
            .join(VotingSessionControversy.voting_session)
            .outerjoin(vote_subquery)
            .order_by(VotingSession.date.desc())
        )

        def meaning(vote_choice, controversy):
            if vote_choice == 'yes':
                return controversy.vote_meaning_yes
            elif vote_choice == 'no':
                return controversy.vote_meaning_no
            else:
                return None

        rv['controversy_list'] = [
            {
                'id': controversy.id,
                'title': controversy.title,
                'date': vs_date,
                'choice': vote_choice or 'novote',
                'meaning': meaning(vote_choice, controversy),
                #'press_link_list': controversy.press_links.split(),
            }
            for controversy, vs_date, vote_choice in controversy_query
        ]

        rv['contact'] = {
            'website_url': self.person.website_url,
            'blog_url': self.person.blog_url,
            'email_value': self.person.email_value,
            'facebook_url': self.person.facebook_url,
            'twitter_url': self.person.twitter_url,
            'phone': self.mandate.phone,
            'address': self.mandate.address,
        }

        rv['assets'] = self.get_assets_data()

        rv['top_words'] = get_top_words(self.mandate.id, 50)

        return rv

    def get_recent_activity(self, limit=None, limit_each=None):
        recent_transcripts_query = (
            self.mandate.transcripts
            .order_by(Transcript.serial.desc())
            .options(joinedload('chapter'))
        )
        if limit_each is not None:
            recent_transcripts_query = (
                recent_transcripts_query
                .limit(limit_each)
            )
        recent_transcripts = [
            {
                'date': t.chapter.date,
                'text': filters.do_truncate(t.text, 200),
                'type': 'speech',
                'chapter_serial': t.chapter.serial,
                'serial_id': t.serial_id,
            }
            for t in recent_transcripts_query
        ]

        recent_questions = _get_recent_questions(self.mandate, limit_each)
        recent_proposals = _get_recent_proposals(self.mandate, limit_each)

        rv = recent_transcripts + recent_questions + recent_proposals
        rv.sort(key=lambda r: r['date'], reverse=True)
        if limit is not None:
            rv = rv[:limit]

        return rv

    def get_stats(self):
        rv = {}
        voting_session_count = (
            VotingSession.query
            .filter(VotingSession.final == True)
            .filter(VotingSession.date >= self.mandate.interval.lower)
            .filter(VotingSession.date < self.mandate.interval.upper)
            .count()
        )
        final_votes = (
            self.mandate.votes
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
        )
        votes_attended = final_votes.count()
        votes_loyal = final_votes.filter(Vote.loyal == True).count()

        rv['vote'] = {
            'attendance': votes_attended / voting_session_count,
        }
        if votes_attended > 0:
            rv['vote']['loyalty'] = votes_loyal / votes_attended

            votes_with_cabinet = (
                final_votes
                .filter(Vote.loyal_to_cabinet != None)
                .count()
            )
            if votes_with_cabinet:
                votes_cabinet_loyal = (
                    final_votes
                    .filter(Vote.loyal_to_cabinet == True)
                    .count()
                )
                rv['vote']['cabinet_loyalty'] = (
                    votes_cabinet_loyal / votes_with_cabinet
                )

        rv['speeches'] = self.mandate.transcripts.count()
        rv['questions'] = self.mandate.asked.count()
        rv['proposals'] = self.mandate.sponsorships.count()
        rv['proposals_accepted'] = (
            self.mandate.sponsorships
            .join(Sponsorship.proposal)
            .filter_by(status='approved')
            .count()
        )
        rv['local_score'] = self._local_ask_query.count()

        rv['committee_attendance'] = [
            {
                'attendance_2013': row.attendance_2013,
                'committee': row.committee_name,
            }
            for row in (
                db.session.query(
                    MpCommitteeMembership.attendance_2013,
                    MpCommittee.name.label('committee_name'),
                )
                .filter(MpCommitteeMembership.mandate == self.mandate)
                .join(MpCommitteeMembership.mp_committee)
                .filter(MpCommitteeMembership.attendance_2013 != None)
            )
        ]

        return rv

    def get_assets_data(self):
        assets = self.person.asset_statements.order_by('date').first()
        if assets:
            return {
                'net_worth_eur': assets.net_worth_eur,
                'land_agri_area': assets.land_agri_area,
                'land_city_area': assets.land_city_area,
                'realty_count': assets.realty_count,
                'vehicle_count': assets.vehicle_count,
                'year_income_eur': assets.year_income_eur,
                'raw_data': assets.raw_data,
            }

        else:
            return {}

    def get_local_activity(self):
        return {
            'question_list': [
                {
                    'id': ask.question.id,
                    'date': ask.question.date,
                    'title': ask.question.title,
                }
                for ask in (
                    self._local_ask_query
                    .options(joinedload('question'))
                    .join(Ask.question)
                    .order_by(Question.date.desc())
                )
            ],
        }

    def get_questions(self):
        return [
            {
                'id': ask.question.id,
                'date': ask.question.date,
                'title': ask.question.title,
            }
            for ask in (
                self.mandate.asked
                .options(joinedload('question'))
                .join(Ask.question)
                .order_by(Question.date.desc())
            )
        ]

    def get_proposals(self):
        return [
            {
                'id': sp.proposal.id,
                'title': sp.proposal.title,
                'status': sp.proposal.status,
                'tacit_approval': pluck_tacit_approval(sp.proposal),
                'controversy': sp.proposal.controversy.all(),
            }
            for sp in (
                self.mandate.sponsorships
                .options(joinedload('proposal'))
                .join(Sponsorship.proposal)
                .order_by(Proposal.date.desc())
            )
        ]

    def get_group_history(self):
        membership_query = (
            self.mandate.group_memberships
            .order_by(MpGroupMembership.interval.desc())
        )
        group_history = [
            {
                'start_date': membership.interval.lower,
                'end_date': membership.interval.upper,
                'role': membership.role,
                'group_short_name': membership.mp_group.short_name,
            }
            for membership in membership_query
        ]
        return group_history

    def get_activitychart_data(self):
        days = [date(2012, 12, 17) + timedelta(weeks=w) for w in range(52 * 4)]

        vacations = [
            (date(2012, 12, 24), date(2013, 1, 21)),
            (date(2013, 7, 1), date(2013, 9, 2)),
            (date(2013, 12, 30), date(2014, 2, 3)),
        ]

        proposals_by_day = group_by_week(
            db.session.query(
                Proposal.date,
                func.count('*'),
            )
            .join(Proposal.sponsorships)
            .filter(Sponsorship.mandate_id == self.mandate.id)
            .filter(Proposal.date >= days[0])
            .group_by(Proposal.date)
        )

        questions_by_day = group_by_week(
            db.session.query(
                Question.date,
                func.count('*'),
            )
            .join(Question.asked)
            .filter(Ask.mandate_id == self.mandate.id)
            .filter(Question.date >= days[0])
            .group_by(Question.date)
        )

        series = []
        for day in days:
            series.append({
                'date': day,
                'proposals': proposals_by_day.get(day, 0),
                'questions': questions_by_day.get(day, 0),
                'vacation': any(d0 <= day < d1 for d0, d1 in vacations),
            })

        return series

    def get_votes_data(self):
        query = (
            db.session.query(
                VotingSession,
                Vote,
                GroupVote,
                MpGroup,
            )
            .filter(VotingSession.final == True)
            .join(Vote)
            .filter(Vote.mandate == self.mandate)
            .join(VotingSession.group_votes)
            .join(GroupVote.mp_group)
            .join(MpGroup.memberships)
            .filter(MpGroupMembership.interval.contains(VotingSession.date))
            .filter(MpGroupMembership.mandate == self.mandate)
            .order_by(VotingSession.date.desc(), VotingSession.cdeppk.desc())
        )

        return [
            {
                'subject': vs.subject,
                'date': vs.date,
                'person_choice': vote.choice,
                'group_short_name': mp_group.short_name,
                'group_choice': group_vote.choice,
                'cabinet_choice': vs.cabinet_choice,
            }
            for vs, vote, group_vote, mp_group in query
        ]

    def get_top_policies(self):
        count_map = defaultdict(int)

        question_query = (
            db.session.query(
                PolicyDomain.id,
                func.count('*'),
            )
            .select_from(Question)
            .join(Question.asked)
            .filter_by(mandate=self.mandate)
            .outerjoin(Question.policy_domain)
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
            .filter(Proposal.date >= LEGISLATURE_2012_START)
            .join(Proposal.sponsorships)
            .filter_by(mandate=self.mandate)
            .outerjoin(Proposal.policy_domain)
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

    def get_policy(self, policy_slug):
        policy = PolicyDomain.query.filter_by(slug=policy_slug).first()
        if policy is None:
            raise self.missing()

        return {
            'name': policy.name,
            'proposal_list': self.dal.get_policy_proposal_list(
                policy_slug, mandate=self.mandate),
            'question_list': self.dal.get_policy_question_list(
                policy_slug, mandate=self.mandate),
        }

    def get_comparison_lists(self):
        def person_data(person):
            return {'slug': person.slug, 'name': person.name_first_last}

        rv = {}

        today = date.today()

        same_county_query = (
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .filter_by(county=self.mandate.county)
        )

        if today in self.mandate.interval:
            mp_group = (
                MpGroup.query
                .join(MpGroup.memberships)
                .filter_by(mandate=self.mandate)
                .filter(MpGroupMembership.interval.contains(today))
                .first()
            )

            if mp_group is not None:
                same_party_query = (
                    Person.query
                    .join(Person.mandates)
                    .filter_by(year=2012)
                    .join(Mandate.group_memberships)
                    .filter(MpGroupMembership.interval.contains(today))
                    .filter_by(mp_group=mp_group)
                )

                rv.update({
                    'party_short_name': mp_group.short_name,
                    'same_party': [person_data(p) for p in same_party_query],
                })

        mandate_count = Mandate.query.filter_by(person=self.person).count()

        mandate_count_subquery = (
            db.session.query(Mandate.person_id)
            .group_by(Mandate.person_id)
            .having(func.count(Mandate.id) == mandate_count)
            .subquery()
        )

        same_mandate_count_query = (
            Person.query
            .join(mandate_count_subquery)
            .join(Person.mandates)
            .filter_by(year=2012)
        )

        same_position_category = []
        category_query = (
            self.person.positions
            .filter(Position.interval.contains(date.today()))
        )
        for position in category_query:
            same_category_query = (
                Person.query
                .join(Person.positions)
                .filter(Position.category == position.category)
                .join(Person.mandates)
                .filter(Mandate.year == 2012)
                .join(Mandate.chamber)
                .filter_by(slug='cdep')
            )
            person_list = [person_data(p) for p in same_category_query]
            if person_list:
                same_position_category.append({
                    'category': position.category,
                    'person_list': person_list,
                })

        committee_president_query = (
            Person.query
            .join(Person.mandates)
            .filter(Mandate.year == 2012)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(Mandate.committee_memberships)
            .filter(
                func.lower(MpCommitteeMembership.role)
                .contains('preşedinte')
            )
        )

        is_committee_president = (
            committee_president_query
            .filter(Person.id == self.person.id)
            .count() > 0
        )
        if is_committee_president:
            same_position_category.append({
                'category': 'committee-president',
                'person_list': [person_data(p) for p in
                                committee_president_query],
            })

        rv.update({
            'mandate_count': mandate_count,
            'same_mandate_count': [person_data(p) for p in
                                   same_mandate_count_query],
            'same_position_category': same_position_category,
        })

        if self.mandate.county:
            rv.update({
                'county_name': self.mandate.county.name,
                'same_county': [person_data(p) for p in same_county_query],
            })

        return rv

    def get_transcript_list(self):
        transcripts_query = (
            self.mandate.transcripts
            .options(joinedload('chapter'))
            .order_by(Transcript.serial)
        )
        return [
            {
                'date': tr.chapter.date,
                'text': tr.text,
                'serial': tr.serial,
                'serial_id': tr.serial_id,
                'chapter_serial': tr.chapter.serial,
                'type': 'speech',
            }
            for tr in transcripts_query
        ]

    def get_voting_similarity(self, other_person):
        vote_1 = aliased(Vote)
        vote_2 = aliased(Vote)
        vote_query = (
            db.session.query(VotingSession.id)
            .join(vote_1)
            .filter(vote_1.mandate == self.mandate)
            .join(vote_2)
            .filter(vote_2.mandate == other_person.mandate)
            .filter((vote_1.choice != None) | (vote_2.choice != None))
        )
        similar_vote_query = (
            vote_query
            .filter(vote_1.choice == vote_2.choice)
        )
        vote_count = vote_query.count()
        if vote_count > 0:
            return similar_vote_query.count() / vote_count
        else:
            return None

    def get_voting_similarity_list(self):
        other_mandate = aliased(Mandate)
        other_vote = aliased(Vote)
        my_vote = aliased(Vote)
        similarity_cte = (
            db.session.query(
                other_vote.mandate_id,
                func.count(other_vote.id).label('count'),
            )
            .join(
                my_vote,
                (my_vote.choice == other_vote.choice) &
                (my_vote.voting_session_id == other_vote.voting_session_id),
            )
            .filter(my_vote.mandate == self.mandate)
            .group_by(other_vote.mandate_id)
            .cte()
        )

        similarity_query = (
            db.session.query(
                Person,
                similarity_cte.c.count,
                MpGroup.short_name,
            )
            .join(Person.mandates)
            .filter_by(year=2012)
            .join(similarity_cte, similarity_cte.c.mandate_id == Mandate.id)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.interval.contains(date.today()))
            .join(MpGroupMembership.mp_group)
        )

        count_list = similarity_query.all()
        self_count_list = [c for p, c, n in count_list if p == self.person]
        self_count = self_count_list[0] if self_count_list else None

        rv = [
            {
                'person_slug': person.slug,
                'name': person.name_first_last,
                'similarity': count / self_count,
                'party_short_name': party_short_name,
            }
            for person, count, party_short_name in
            (count_list if self_count else [])
            if person != self.person
        ]

        rv.sort(key=lambda r: r['similarity'], reverse=True)
        return rv


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
            .filter_by(year=2012)
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


class DalParty:

    def __init__(self, dal, short_name, year=2012, missing=KeyError):
        self.dal = dal

        self.party = (
            MpGroup.query
            .filter_by(short_name=short_name)
            .filter_by(year=year)
            .first()
        )
        if self.party is None:
            raise missing()

    def get_name(self):
        return self.party.short_name

    def get_main_details(self):
        return {
            'name': self.party.name,
            'short_name': self.party.short_name,
        }

    def get_details(self):
        rv = self.get_main_details()

        rv['member_list'] = self.get_members()
        rv['loyalty'] = self._get_loyalty()
        rv['questions'] = self._get_questions()
        rv['description'] = self.party.description

        return rv

    def get_members(self):
        member_list = []
        memberships_query = (
            self.party.memberships
            .filter(
                MpGroupMembership.interval.contains(date.today())
            )
            .options(
                joinedload('mandate'),
                joinedload('mandate.person'),
            )
            .join(MpGroupMembership.mandate)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(Mandate.person)
            .order_by(Person.first_name, Person.last_name)
        )

        for membership in memberships_query:
            person = membership.mandate.person
            member_list.append({
                'name': person.name_first_last,
                'slug': person.slug,
            })
        return member_list

    def _get_loyalty(self):

        def _loyal_percent(vote_query):
            total = vote_query.count()
            loyal = vote_query.filter(Vote.loyal == True).count()
            if total:
                return loyal / total
            else:
                return None

        rv = {
            'by-category': {},
            'by-mandate-count': {},
        }

        final_votes = (
            Vote.query
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
            .join(Vote.mandate)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(VotingSession.date))
        )
        rv['all'] = _loyal_percent(final_votes)

        group_votes = GroupVote.query.filter(GroupVote.mp_group == self.party)
        n_group_votes = group_votes.count()
        if n_group_votes > 0:
            loyal_group_votes = group_votes.filter_by(loyal_to_cabinet=True)
            rv['to-cabinet'] = loyal_group_votes.count() / n_group_votes

        position_category_list = [
            row[0] for row in
            db.session.query(distinct(Position.category))
        ]
        for category in position_category_list:
            members_with_position_cte = (
                db.session.query(
                    distinct(Mandate.id).label('mandate_id'),
                    Position.interval.label('interval'),
                )
                .join(Mandate.person)
                .join(Person.positions)
                .filter(Position.category == category)
                .cte()
            )

            category_final_votes = (
                final_votes
                .join(
                    members_with_position_cte,
                    Mandate.id == members_with_position_cte.c.mandate_id,
                )
                .filter(
                    members_with_position_cte.c.interval.contains(
                        VotingSession.date
                    )
                )
            )

            loyalty = _loyal_percent(category_final_votes)
            if loyalty is not None:
                rv['by-category'][category] = loyalty

        mandate_count_cte = (
            db.session.query(
                Mandate.person_id.label('person_id'),
                func.count('*').label('mandate_count'),
            )
            .group_by(Mandate.person_id)
            .cte()
        )

        one_mandate_cte = (
            db.session.query(Mandate.id.label('mandate_id'))
            .join(
                mandate_count_cte,
                Mandate.person_id == mandate_count_cte.c.person_id,
            )
            .filter(mandate_count_cte.c.mandate_count == 1)
            .cte()
        )

        one_mandate_final_votes = (
            final_votes
            .join(
                one_mandate_cte,
                Mandate.id == one_mandate_cte.c.mandate_id,
            )
        )
        loyalty = _loyal_percent(one_mandate_final_votes)
        rv['by-mandate-count']['one'] = loyalty

        multiple_mandate_cte = (
            db.session.query(Mandate.id.label('mandate_id'))
            .join(
                mandate_count_cte,
                Mandate.person_id == mandate_count_cte.c.person_id,
            )
            .filter(mandate_count_cte.c.mandate_count > 1)
            .cte()
        )

        one_mandate_final_votes = (
            final_votes
            .join(
                multiple_mandate_cte,
                Mandate.id == multiple_mandate_cte.c.mandate_id,
            )
        )
        loyalty = _loyal_percent(one_mandate_final_votes)
        rv['by-mandate-count']['multiple'] = loyalty

        return rv

    def _get_questions(self):
        question_query = (
            db.session.query(
                distinct(Question.id),
            )
            .join(Question.asked)
            .join(Ask.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(Question.date))
        )

        local_question_query = (
            question_query
            .join(Ask.match_row)
            .filter(Match.score > 0)
        )

        return {
            'total': question_query.count(),
            'local': local_question_query.count(),
        }

    def get_top_policies(self, cutoff=0.05):
        count_map = defaultdict(int)

        question_query = (
            db.session.query(
                PolicyDomain.id,
                func.count(distinct(Question.id)),
            )
            .select_from(Question)
            .join(Question.asked)
            .join(Ask.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(Question.date))
            .outerjoin(Question.policy_domain)
            .group_by(PolicyDomain.id)
        )
        for policy_domain_id, count in question_query:
            count_map[policy_domain_id] += count

        proposal_query = (
            db.session.query(
                PolicyDomain.id,
                func.count(distinct(Proposal.id)),
            )
            .select_from(Proposal)
            .filter(Proposal.date >= LEGISLATURE_2012_START)
            .join(Proposal.sponsorships)
            .join(Sponsorship.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(Proposal.date))
            .outerjoin(Proposal.policy_domain)
            .group_by(PolicyDomain.id)
        )
        for policy_domain_id, count in proposal_query:
            count_map[policy_domain_id] += count

        total = sum(count_map.values())

        policy_list = []
        if total:
            for policy_domain in PolicyDomain.query:
                interest = count_map.get(policy_domain.id, 0) / total
                if interest > cutoff:
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

    def get_policy(self, policy_slug):
        policy = PolicyDomain.query.filter_by(slug=policy_slug).first()
        if policy is None:
            raise self.missing()

        return {
            'name': policy.name,
            'proposal_list': self.dal.get_policy_proposal_list(
                policy_slug, party=self.party),
            'question_list': self.dal.get_policy_question_list(
                policy_slug, party=self.party),
        }

    def get_policy_members(self, policy_slug):
        policy = PolicyDomain.query.filter_by(slug=policy_slug).first()
        if policy is None:
            raise self.missing()

        question_cte = (
            db.session.query(
                Mandate.id.label('mandate_id'),
                func.count(Ask.id).label('ask_count'),
            )
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(date.today()))
            .join(Mandate.asked)
            .join(Ask.question)
            .filter(MpGroupMembership.interval.contains(Question.date))
            .group_by(Mandate.id)
            .cte()
        )

        proposal_cte = (
            db.session.query(
                Mandate.id.label('mandate_id'),
                func.count(Sponsorship.id).label('sponsorship_count'),
            )
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(date.today()))
            .join(Mandate.sponsorships)
            .join(Sponsorship.proposal)
            .filter(MpGroupMembership.interval.contains(Proposal.date))
            .group_by(Mandate.id)
            .cte()
        )

        action_count = (
            question_cte.c.ask_count +
            proposal_cte.c.sponsorship_count
        ).label('action_count')

        action_query = (
            db.session.query(
                Person,
                action_count,
            )
            .join(Person.mandates)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == self.party)
            .filter(MpGroupMembership.interval.contains(date.today()))
            .outerjoin(question_cte, question_cte.c.mandate_id == Mandate.id)
            .outerjoin(proposal_cte, proposal_cte.c.mandate_id == Mandate.id)
            .filter(action_count != None)
            .order_by(desc('action_count'))
        )

        results = list(action_query)

        total = sum(n for _, n  in results)
        top_count = 0
        top_95 = []
        for person, n in results:
            top_count += n
            top_95.append((person, n))
            if top_count / total > .95:
                break

        return [
            {
                'name': person.name_first_last,
                'slug': person.slug,
                'action_count': n,
            }
            for person, n in top_95
        ]

    def get_member_count(self):
        query = (
            MemberCount.query
            .filter_by(short_name=self.party.short_name)
            .order_by('year')
        )
        return [
            dict(year=mc.year, count=mc.count)
            for mc in query
        ]


class DataAccess:

    def __init__(self, missing=KeyError):
        self.missing = missing

    def get_county_name_map(self):
        return {c.code: c.name for c in County.query}

    def get_2012_mandates_by_county(self):
        mandates = (
            Mandate.query
            .filter_by(year=2012)
            .join(Mandate.person)
            .join(Mandate.county)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
        )

        mandate_data = defaultdict(list)
        for m in mandates:
            key = '%s%d' % (m.county.code, m.college)
            mandate_data[key].append({
                'name': m.person.name_first_last,
                'person_slug': m.person.slug,
            })

        return dict(mandate_data)

    def search_person_by_name(self, name_query):
        name_search = NameSearch(
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
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

        activity_count = (
            proposals_cte.c.proposal_count +
            questions_cte.c.question_count
        )

        activity_query = (
            db.session.query(
                Person,
                activity_count,
            )
            .join(Mandate.person)
            .filter(Mandate.year == 2012)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
            .join(proposals_cte, proposals_cte.c.mandate_id == Mandate.id)
            .join(questions_cte, questions_cte.c.mandate_id == Mandate.id)
            .order_by(activity_count.desc())
        )

        return [
            {
                'name': person.name_first_last,
                'slug': person.slug,
                'count': count,
            }
            for person, count in activity_query
        ]

    def search_person_by_contracts(self, contracts_query):
        person_query = (
            Person.query
            .join(Mandate.person)
            .filter(Mandate.year == 2012)
            .join(Mandate.chamber)
            .filter_by(slug='cdep')
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
        return self.get_policy_controversy_qs().count()

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

    def get_party_qs(self, year=2012):
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

    def get_group_membership(self, interval, end):
        null_end = lambda d: None if d.year == 9999 else d
        (q_lower, q_upper) = interval
        membership_lower = func.lower(MpGroupMembership.interval)
        membership_upper = func.upper(MpGroupMembership.interval)

        membership_query = (
            MpGroupMembership.query
            .join(MpGroupMembership.mp_group)
            .join(MpGroupMembership.mandate)
            .filter_by(year=2012)
            .filter((
                (q_lower <= membership_lower) &
                ((membership_lower < q_upper) if q_upper else True)
            ) | (
                (q_lower < membership_upper) &
                ((membership_upper <= q_upper) if q_upper else True)
            ))
            .options(
                joinedload('mp_group'),
                joinedload('mandate'),
                joinedload('mandate.person'),
            )
            .order_by(
                MpGroupMembership.mandate_id,
                MpGroupMembership.interval,
            )
        )

        if end:
            membership_query = (
                membership_query
                .filter(membership_upper == func.upper(Mandate.interval))
            )

        else:
            membership_query = (
                membership_query
                .filter(func.upper(Mandate.interval) >= q_upper)
            )

        return (
            {
                'name': membership.mandate.person.name_first_last,
                'group': membership.mp_group.name,
                'start': membership.interval.lower,
                'end': null_end(membership.interval.upper),
            }
            for membership in membership_query
        )

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
            .filter(Proposal.date >= LEGISLATURE_2012_START)
            .filter(
                Proposal.activity.like('%' + TACIT_APPROVAL_SUBSTRING + '%')
            )
        )

    def get_policy_proposal_list(self, policy_slug=None, mandate=None, party=None):
        proposal_query = (
            db.session.query(
                distinct(Proposal.id)
            )
            .filter(Proposal.date >= LEGISLATURE_2012_START)
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

        return [
            {
                'title': proposal.title,
                'id': proposal.id,
                'status': proposal.status,
                'tacit_approval': pluck_tacit_approval(proposal),
                'controversy': proposal.controversy.all(),
            }
            for proposal in (
                Proposal.query
                .filter(Proposal.id.in_([r[0] for r in proposal_query]))
                .order_by(Proposal.date)
            )
        ]

    def get_policy_tacit_approval_list(self, limit=None):
        qs = (
            self.get_policy_tacit_approval_qs()
            .order_by(Proposal.date.desc())
        )
        if limit:
            qs = qs.limit(limit)
        rv = [
            {
                'title': proposal.title,
                'id': proposal.id,
                'status': proposal.status,
                'tacit_approval': pluck_tacit_approval(proposal),
                'controversy': proposal.controversy.all(),
            }
            for proposal in qs
        ]
        rv.sort(key=lambda r: r['tacit_approval']['date'], reverse=True)
        return rv

    def get_policy_tacit_approval_count(self):
        return self.get_policy_tacit_approval_qs().count()

    def get_policy_controversy_qs(self):
        return Proposal.query.join(ProposalControversy)

    def get_policy_controversy_list(self, limit=None):
        qs = (
            self.get_policy_controversy_qs()
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
            }
            for proposal in qs
        ]

    def get_policy_controversy_count(self):
        return self.get_policy_controversy_qs().count()

    def get_policy_question_list(self, policy_slug=None, mandate=None, party=None):
        question_query = (
            db.session.query(
                distinct(Question.id),
            )
            .outerjoin(Question.policy_domain)
            .filter(Question.date >= LEGISLATURE_2012_START)
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
            .filter(MpGroup.year == 2012)
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
            .filter(Proposal.date >= LEGISLATURE_2012_START)
            .join(Proposal.sponsorships)
            .join(Sponsorship.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.interval.contains(Proposal.date))
            .join(Proposal.policy_domain)
            .filter(PolicyDomain.slug == policy_slug)
            .join(MpGroupMembership.mp_group)
            .filter(MpGroup.year == 2012)
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
            .filter_by(year=2012)
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
            .filter_by(year=2012)
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
            .filter_by(year=2012)
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
            .filter_by(year=2012)
            .outerjoin(Question.policy_domain)
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
            .filter(Proposal.date >= LEGISLATURE_2012_START)
            .join(Proposal.sponsorships)
            .join(Sponsorship.mandate)
            .filter_by(year=2012)
            .outerjoin(Proposal.policy_domain)
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


def get_top_words(mandate_id, number):
    query = WORDCLOUD_SQL % {'mandate_id': mandate_id, 'number': number}
    return list(tuple(r) for r in db.session.execute(query))


WORDCLOUD_SQL = """\
WITH words AS (
    SELECT unnest(regexp_split_to_array(lower(text), '\M\W*\m')) AS word
    FROM ocr_text
    JOIN proposal ON ocr_text.id = proposal.id
    JOIN sponsorship ON proposal.id = sponsorship.proposal_id
    WHERE sponsorship.mandate_id = '%(mandate_id)s'
)
SELECT word, count(*) as n FROM words
WHERE char_length(word) > 4
  AND unaccent(word) NOT IN (SELECT id FROM stopword)
GROUP BY word
ORDER BY n DESC
LIMIT %(number)d;
"""
