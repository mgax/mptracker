from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from jinja2 import filters
from mptracker.models import (
    County,
    Person,
    Mandate,
    MpGroup,
    MpGroupMembership,
    MpCommitteeMembership,
    Proposal,
    ProposalActivityItem,
    Sponsorship,
    TranscriptChapter,
    Transcript,
    Question,
    Ask,
    Match,
    VotingSession,
    Controversy,
    Vote,
    GroupVote,
    PolicyDomain,
    NameSearch,
    db,
)


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
                Controversy.title,
                VotingSession.date,
                vote_subquery.c.choice,
            )
            .join(Controversy.voting_sessions)
            .outerjoin(vote_subquery)
        )
        rv['controversy_list'] = [
            {
                'title': contro_title,
                'date': vs_date,
                'choice': vote_choice or 'novote',
            }
            for contro_title, vs_date, vote_choice in controversy_query
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

        if self.mandate.picture_url is not None:
            rv['picture_filename'] = '%s-300px.jpg' % str(self.mandate.id)

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
        rv['local_score'] = self._local_ask_query.count()
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
                'date': sp.proposal.date,
                'title': sp.proposal.title,
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

    def get_top_policies(self, cutoff=0.1):
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

        print(self.dal.get_policy_proposal_list(
                policy_slug, self.mandate))
        return {
            'name': policy.name,
            'proposal_list': self.dal.get_policy_proposal_list(
                policy_slug, self.mandate),
            'question_list': self.dal.get_policy_question_list(
                policy_slug, self.mandate),
        }

    def get_comparison_lists(self):
        def person_data(person):
            return {'slug': person.slug, 'name': person.name_first_last}

        today = date.today()

        same_county_query = (
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .filter_by(county=self.mandate.county)
        )

        mp_group = (
            MpGroup.query
            .join(MpGroup.memberships)
            .filter_by(mandate=self.mandate)
            .filter(MpGroupMembership.interval.contains(today))
            .first()
        )

        same_party_query = (
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.interval.contains(today))
            .filter_by(mp_group=mp_group)
        )

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

        return {
            'county_name': self.mandate.county.name,
            'same_county': [person_data(p) for p in same_county_query],
            'party_short_name': mp_group.short_name,
            'same_party': [person_data(p) for p in same_party_query],
            'mandate_count': mandate_count,
            'same_mandate_count': [person_data(p) for p in
                                   same_mandate_count_query],
        }

    def get_transcript_list(self):
        transcripts_query = (
            self.mandate.transcripts
            .options(joinedload('chapter'))
            .order_by(Transcript.serial)
        )
        return [
            {
                'date': tr.chapter.date,
                'serial': tr.serial,
                'text': tr.text,
            }
            for tr in transcripts_query
        ]


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

    def get_2012_mandates_by_county(self):
        mandates = (
            Mandate.query
            .filter_by(year=2012)
            .join(Mandate.person)
            .join(Mandate.county)
        )

        mandate_data = defaultdict(list)
        for m in mandates:
            key = '%s%d' % (m.county.code, m.college)
            mandate_data[key].append({
                'name': m.person.name_first_last,
                'person_slug': m.person.slug,
            })

        return dict(mandate_data)

    def search_person(self, query):
        name_search = NameSearch(
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .order_by(Person.first_name, Person.last_name)
        )
        return [
            {'name': person.name_first_last, 'slug': person.slug}
            for person in name_search.find(query.strip())
        ]

    def get_person(self, person_slug):
        return DalPerson(person_slug, self, self.missing)

    def get_county(self, county_code):
        return DalCounty(county_code, self.missing)

    def get_recent_proposals(self):
        return _get_recent_proposals(None, 10)

    def get_recent_questions(self):
        return _get_recent_questions(None, 10)

    def get_question_details(self, question_id):
        question = Question.query.get(question_id)
        if question is None:
            raise self.missing()

        rv = {'title': question.title, 'text': question.text}

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

        return rv

    def get_party_list(self):
        return [
            {'name': group.name, 'short_name': group.short_name}
            for group in MpGroup.query.order_by(MpGroup.name)
            if group.short_name not in ['Indep.', 'Mino.']
        ]

    def get_party_details(self, party_short_name):
        party = MpGroup.query.filter_by(short_name=party_short_name).first()
        if party is None:
            raise self.missing()
        rv = {'name': party.name}

        rv['member_list'] = []
        memberships_query = (
            party.memberships
            .filter(
                MpGroupMembership.interval.contains(date.today())
            )
            .options(
                joinedload('mandate'),
                joinedload('mandate.person'),
            )
            .join(MpGroupMembership.mandate)
            .join(Mandate.person)
            .order_by(Person.first_name, Person.last_name)
        )
        for membership in memberships_query:
            person = membership.mandate.person
            rv['member_list'].append({
                'name': person.name_first_last,
                'slug': person.slug,
            })

        final_votes = (
            Vote.query
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
            .join(Vote.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group == party)
        )
        votes_attended = final_votes.count()
        votes_loyal = final_votes.filter(Vote.loyal == True).count()
        rv['member_loyalty'] = votes_loyal / votes_attended

        group_votes = GroupVote.query.filter(GroupVote.mp_group == party)
        n_group_votes = group_votes.count()
        if n_group_votes > 0:
            loyal_group_votes = group_votes.filter_by(loyal_to_cabinet=True)
            rv['cabinet_loyalty'] = loyal_group_votes.count() / n_group_votes

        return rv

    def get_policy_list(self):
        return [
            {'name': policy.name, 'slug': policy.slug}
            for policy in PolicyDomain.query
        ]

    def get_policy(self, policy_slug):
        policy = PolicyDomain.query.filter_by(slug=policy_slug).first()
        if policy is None:
            raise self.missing()
        return {'name': policy.name}

    def get_policy_proposal_list(self, policy_slug, mandate=None):
        proposal_query = (
            Proposal.query
            .join(Proposal.policy_domain)
            .filter_by(slug=policy_slug)
        )
        if mandate is not None:
            proposal_query = (
                proposal_query
                .join(Proposal.sponsorships)
                .filter_by(mandate=mandate)
            )
        return [
            {
                'title': proposal.title,
                'id': proposal.id,
                'status': proposal.status,
            }
            for proposal in proposal_query
        ]

    def get_policy_question_list(self, policy_slug, mandate=None):
        question_query = (
            Question.query
            .join(Question.policy_domain)
            .filter_by(slug=policy_slug)
            .filter(Question.date >= date(2012, 12, 17))
            .order_by(Question.date.desc())
        )
        if mandate is not None:
            question_query = (
                question_query
                .join(Question.asked)
                .filter_by(mandate=mandate)
            )
        return [
            {
                'title': question.title,
                'id': question.id,
                'date': question.date,
                'type': question.type,
            }
            for question in question_query
        ]

    def get_proposal_details(self, proposal_id):
        proposal = Proposal.query.get(proposal_id)
        if proposal is None:
            raise self.missing()
        rv = {'title': proposal.title}

        rv['activity'] = []
        activity_query = (
            proposal.activity
            .order_by(ProposalActivityItem.order.desc())
        )
        for item in activity_query:
            rv['activity'].append({
                'date': item.date,
                'location': item.location.lower(),
                'html': item.html,
            })

        sponsors_query = (
            Person.query
            .join(Person.mandates)
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
            .join(Mandate.person)
            .order_by(Transcript.serial)
        )
        rv['transcript_list'] = [
            {
                'text': transcript.text,
                'person_name': person.name_first_last,
                'person_slug': person.slug,
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
  AND word NOT IN (SELECT id FROM stopword)
GROUP BY word
ORDER BY n DESC
LIMIT %(number)d;
"""
