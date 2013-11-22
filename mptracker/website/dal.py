from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from mptracker.models import (
    Person,
    Mandate,
    MpGroup,
    MpGroupMembership,
    Proposal,
    VotingSession,
    Vote,
    PolicyDomain,
)


class DataAccess:

    def search_person(self, query):
        sql_query = (
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .filter(func.lower(Person.name).like('%' + query.lower() + '%'))
            .order_by(Person.name)
        )
        return [
            {'name': person.name, 'id': person.id}
            for person in sql_query.all()
        ]

    def get_person(self, person_id, missing=KeyError):
        person = Person.query.get(person_id)
        if person is None:
            raise missing()
        return {'name': person.name}

    def get_mandate2012_details(self, person_id):
        mandate = (
            Mandate.query
            .filter_by(person_id=person_id)
            .filter_by(year=2012)
            .first()
        )

        membership_query = (
            mandate.group_memberships
            .order_by(MpGroupMembership.interval.desc())
        )
        group_history = [
            {
                'start_date': membership.interval.lower,
                'end_date': membership.interval.upper,
                'role': membership.role,
                'group_short_name': membership.mp_group.short_name,
                'group_id': membership.mp_group_id,
            }
            for membership in membership_query
        ]

        rv = {'group_history': group_history}

        if mandate.county:
            rv['college'] = {
                'county_name': mandate.county.name,
                'number': mandate.college,
            }

        voting_session_count = (
            VotingSession.query
            .filter(VotingSession.final == True)
            .count()
        )
        final_votes = (
            mandate.votes
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
        )
        votes_attended = final_votes.count()
        votes_loyal = final_votes.filter(Vote.loyal == True).count()

        rv['vote'] = {
            'attendance': votes_attended / voting_session_count,
            'loyalty': votes_loyal / votes_attended,
        }

        rv['speeches'] = mandate.transcripts.count()
        rv['proposals'] = mandate.sponsorships.count()

        return rv

    def get_party_list(self):
        return [
            {'name': group.name, 'id': group.id}
            for group in MpGroup.query.order_by(MpGroup.name)
            if group.short_name not in ['Indep.', 'Mino.']
        ]

    def get_party_details(self, party_id, missing=KeyError):
        party = MpGroup.query.get(party_id)
        if party is None:
            raise missing()
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
            .order_by(Person.name)
        )
        for membership in memberships_query:
            person = membership.mandate.person
            rv['member_list'].append({
                'name': person.name,
                'id': person.id,
            })

        return rv

    def get_policy_list(self):
        return [
            {'name': policy.name, 'id': policy.id}
            for policy in PolicyDomain.query
        ]

    def get_policy(self, policy_id, missing=KeyError):
        policy = PolicyDomain.query.get(policy_id)
        if policy is None:
            raise missing()
        return {'name': policy.name}

    def get_policy_proposal_list(self, policy_id):
        proposal_query = (
            Proposal.query
            .filter_by(policy_domain_id=policy_id)
        )
        return [
            {'title': proposal.title, 'id': proposal.id}
            for proposal in proposal_query
        ]

    def get_proposal(self, proposal_id, missing=KeyError):
        proposal = Proposal.query.get(proposal_id)
        if proposal is None:
            raise missing()
        return {'title': proposal.title}
