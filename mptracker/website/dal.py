from sqlalchemy import func
from mptracker.models import (
    Person,
    Mandate,
    MpGroup,
    MpGroupMembership,
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
        return sql_query.all()

    def get_person(self, person_id, missing=KeyError):
        person = Person.query.get(person_id)
        if person is None:
            raise missing()
        return person

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
            }
            for membership in membership_query
        ]

        return {
            'college': {
                'county_name': mandate.county.name,
                'number': mandate.college,
            },
            'group_history': group_history,
        }

    def get_party_list(self):
        return [
            {'name': group.name, 'id': group.id}
            for group in MpGroup.query.order_by(MpGroup.name)
            if group.short_name not in ['Indep.', 'Mino.']
        ]
