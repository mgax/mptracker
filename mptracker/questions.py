import csv
import flask
from flask.ext.script import Manager


questions_manager = Manager()

@questions_manager.command
def load(csv_path):
    with open(csv_path, 'r') as csv_file:
        csv_doc = csv.DictReader(csv_file)
        for row in csv_doc:
            print(row['person_cdep_id'])
