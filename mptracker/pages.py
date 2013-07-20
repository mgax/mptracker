from collections import defaultdict
from datetime import datetime
import flask
from sqlalchemy.orm import joinedload
from mptracker import models


pages = flask.Blueprint('pages', __name__)


def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()


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
    date_value = parse_date(date_str)
    return flask.render_template('steno_contents.html', **{
        'date': date_value,
        'sections': models.StenoSection.query.filter_by(date=date_value),
    })


@pages.route('/steno/<date_str>/<section_serial_number>')
def steno_section(date_str, section_serial_number):
    date_value = parse_date(date_str)
    section_serial = date_value.strftime('%Y-%m-%d/') + section_serial_number
    section = (models.StenoSection.query
                .filter_by(serial=section_serial)
                .first_or_404())
    if section.date != date_value:
        flask.abort(404)
    return flask.render_template('steno_section.html', **{
        'date': date_value,
        'section': section,
    })
