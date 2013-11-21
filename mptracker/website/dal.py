from sqlalchemy import func
from mptracker.models import (
    Person,
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

    def get_mandate2012_details(self, person):
        mandate = person.mandates.filter_by(year=2012).first()
        return {
            'college': {
                'county_name': mandate.county.name,
                'number': mandate.college,
            }
        }
