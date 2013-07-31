from collections import defaultdict
import calendar
import flask
from sqlalchemy.orm import joinedload
from mptracker import models
from mptracker.common import parse_date


pages = flask.Blueprint('pages', __name__)




@pages.route('/_crashme')
def crashme():
    raise RuntimeError("Crashing, as requested.")


@pages.route('/_ping')
def ping():
    models.Person.query.count()
    return 'mptracker is ok'


@pages.route('/')
def home():
    people = models.Person.query.order_by('name')
    return flask.render_template('home.html', people=people)


@pages.route('/person/<person_id>')
def person(person_id):
    person = models.Person.query.get_or_404(person_id)

    steno_data = defaultdict(list)
    for paragraph in person.steno_paragraphs.order_by('serial'):
        steno_data[paragraph.chapter.date].append(paragraph)

    return flask.render_template('person.html', **{
        'person': person,
        'steno_data': sorted(steno_data.items()),
    })


@pages.route('/steno/')
def steno_calendar():
    date_query = models.db.session.query(models.StenoChapter.date)
    steno_days = set(row[0] for row in date_query.distinct())
    return flask.render_template('steno_calendar.html', **{
        'calendar': calendar.Calendar(),
        'steno_days': steno_days,
    })


@pages.route('/steno/<date_str>')
def steno_contents(date_str):
    date_value = parse_date(date_str)
    return flask.render_template('steno_contents.html', **{
        'date': date_value,
        'chapters': models.StenoChapter.query.filter_by(date=date_value),
    })


@pages.route('/steno/<date_str>/<chapter_serial_number>')
def steno_chapter(date_str, chapter_serial_number):
    date_value = parse_date(date_str)
    chapter_serial = date_value.strftime('%Y-%m-%d/') + chapter_serial_number
    chapter = (models.StenoChapter.query
                .filter_by(serial=chapter_serial)
                .first_or_404())
    if chapter.date != date_value:
        flask.abort(404)
    return flask.render_template('steno_chapter.html', **{
        'date': date_value,
        'chapter': chapter,
    })
