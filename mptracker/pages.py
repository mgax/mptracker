from collections import defaultdict
from datetime import datetime
import flask
from sqlalchemy.orm import joinedload
from mptracker import models


pages = flask.Blueprint('pages', __name__)


@pages.route('/')
def home():
    people = models.Person.query.order_by('name')
    return flask.render_template('home.html', people=people)


@pages.route('/person/<person_id>')
def person(person_id):
    person = models.Person.query.get_or_404(person_id)

    steno_data = defaultdict(list)
    for paragraph in person.steno_paragraphs.order_by('serial'):
        steno_data[paragraph.section.date].append(paragraph)

    return flask.render_template('person.html', **{
        'person': person,
        'steno_data': sorted(steno_data.items()),
    })


@pages.route('/steno/<date_str>')
def steno_contents(date_str):
    date_value = datetime.strptime(date_str, '%Y%m%d').date()
    return flask.render_template('steno_contents.html', **{
        'date': date_value,
        'sections': models.StenoSection.query.filter_by(date=date_value),
    })
