import flask
from mptracker import models

pages = flask.Blueprint('pages', __name__)


@pages.route('/_crashme', methods=['GET', 'POST'])
def crashme():
    if flask.request.method == 'POST':
        raise RuntimeError("Crashing, as requested.")
    else:
        return '<form method="post"><button type="submit">err</button></form>'


@pages.route('/_ping')
def ping():
    models.Person.query.count()
    return 'mptracker is ok'


@pages.route('/')
def home():
    return 'welcome to mptracker website'
