import csv
import logging
import flask
from flask.ext.script import Manager
from mptracker import models


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


questions_manager = Manager()

@questions_manager.command
def load(csv_path):
    person_matcher = models.PersonMatcher()

    existing = set((row.number, row.date) for row in models.Question.query)

    n_add = n_skip = 0
    with open(csv_path, 'r') as csv_file:
        csv_doc = csv.DictReader(csv_file)
        for row in csv_doc:
            row['date'] = models.parse_date(row.pop('date'))
            if (row['number'], row['date']) in existing:
                n_skip += 1
                continue

            person = person_matcher.get_person(row.pop('person_name'),
                                               int(row.pop('person_cdep_id')),
                                               strict=True)
            question = models.Question(person=person, **row)
            models.db.session.add(question)
            n_add += 1
            logger.info("Adding question %s/%s", row['number'], row['date'])

    models.db.session.commit()
    logger.info("Created %d rows, %d were already there.", n_add, n_skip)
