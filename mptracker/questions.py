import csv
import flask
from flask.ext.script import Manager
from mptracker import models


questions_manager = Manager()

@questions_manager.command
def load(csv_path):
    person_matcher = models.PersonMatcher()
    with open(csv_path, 'r') as csv_file:
        csv_doc = csv.DictReader(csv_file)
        for row in csv_doc:
            person = person_matcher.get_person(row.pop('person_name'),
                                               int(row.pop('person_cdep_id')),
                                               strict=True)
            row['date'] = models.parse_date(row.pop('date'))
            question = models.Question(person=person, **row)
            models.db.session.add(question)
    models.db.session.commit()
