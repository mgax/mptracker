from functools import wraps
import flask
from flask.ext.login import LoginManager, current_user
from mptracker import models

login_manager = LoginManager()

auth = flask.Blueprint('auth', __name__)


@login_manager.user_loader
def get_user_by_id(user_id):
    return models.User.query.get(user_id)


@auth.record
def register_login(state):
    login_manager.init_app(state.app)


@auth.route('/login')
def login():
    return flask.render_template('login.html')


def is_privileged():
    if current_user is None or current_user.is_anonymous():
        return False

    app = flask.current_app
    privileged_emails = app.config['PRIVILEGED_EMAILS']
    if current_user.email in privileged_emails:
        return True

    return False


@auth.app_context_processor
def inject_is_privileged():
    return {'current_user_is_privileged': is_privileged()}


def require_privilege(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_privileged():
            return flask.redirect(flask.url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper
