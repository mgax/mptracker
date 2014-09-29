from datetime import date
from collections import defaultdict
from sqlalchemy import func, distinct, desc
from sqlalchemy.orm import joinedload
from mptracker.models import (
    Ask,
    GroupVote,
    Mandate,
    Match,
    MemberCount,
    MpGroup,
    MpGroupMembership,
    Person,
    PolicyDomain,
    Position,
    Proposal,
    Question,
    Sponsorship,
    Vote,
    VotingSession,
    db,
)
from mptracker.website.dal_common import (
    LEGISLATURE_2012_START,
)


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

    @property
    def logo_filename(self):
        return self.party.short_name.lower() + '.jpg'

    def get_details(self):
        rv = self.get_main_details()

        rv['member_list'] = self.get_members()
        rv['loyalty'] = self._get_loyalty()
        rv['questions'] = self._get_questions()

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
            .join(Question.policy_domain)
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
