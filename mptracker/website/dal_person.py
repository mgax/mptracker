from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import joinedload, aliased
from jinja2 import filters
from mptracker.models import (
    Ask,
    GroupVote,
    Mandate,
    Match,
    MpCommittee,
    MpCommitteeMembership,
    MpGroup,
    MpGroupMembership,
    Person,
    PolicyDomain,
    Position,
    Proposal,
    Question,
    Sponsorship,
    Transcript,
    Vote,
    VotingSession,
    VotingSessionControversy,
    db,
)
from mptracker.website.dal_common import (
    LEGISLATURE_2012_START,
    pluck_tacit_approval,
    _get_recent_questions,
    _get_recent_proposals,
)


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


def get_top_words(mandate_id, number):
    query = WORDCLOUD_SQL % {'mandate_id': mandate_id, 'number': number}
    return list(tuple(r) for r in db.session.execute(query))
