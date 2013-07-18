import flask
from mptracker import models


pages = flask.Blueprint('pages', __name__)


@pages.route('/')
def home():
    people = models.Person.query.order_by('name')
    return flask.render_template('home.html', people=people)
