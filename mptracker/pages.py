import flask
from mptracker import models


pages = flask.Blueprint('pages', __name__)


@pages.route('/')
def home():
    people = models.Person.query.order_by('name')
    return flask.render_template('home.html', people=people)


@pages.route('/person/<person_id>')
def person(person_id):
    person = models.Person.query.get_or_404(person_id)
    return flask.render_template('person.html', person=person)
