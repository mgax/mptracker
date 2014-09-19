import flask
from flask.ext.oauthlib.client import OAuth
from flask.ext.principal import (
    Principal, Permission, RoleNeed,
    Identity, identity_changed,
)
import requests

principals = Principal(use_sessions=False)

class role:
    admin = RoleNeed('admin')

class perm:
    admin = Permission(role.admin)

admin = flask.Blueprint('admin', __name__)


def setup_admin(app):
    principals.init_app(app)

    oauth = OAuth(app)
    google = oauth.remote_app(
        'google',
        consumer_key=app.config['GLOGIN_CLIENT_ID'],
        consumer_secret=app.config['GLOGIN_CLIENT_SECRET'],
        request_token_params={
            'scope': 'https://www.googleapis.com/auth/userinfo.email'},
        base_url='https://www.googleapis.com/oauth2/v1/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )

    @app.route('/admin/login')
    def login():
        url = flask.url_for('authorized', _external=True)
        return google.authorize(callback=url)

    @app.route('/admin/logout')
    def logout():
        google_token = flask.session.pop('identity', {}).get('google_token')
        if google_token:
            requests.get(
                'https://accounts.google.com/o/oauth2/revoke',
                params={'token': google_token[0]}
            )
        return flask.redirect(flask.url_for('admin.home'))

    @app.route('/admin/login/google')
    @google.authorized_handler
    def authorized(resp):
        if resp is None:
            return 'Access denied: reason=%s error=%s' % (
                flask.request.args['error_reason'],
                flask.request.args['error_description'],
            )
        flask.session['identity'] = {
            'google_token': (resp['access_token'], ''),
        }
        me = google.get('userinfo')
        flask.session['identity']['name'] = me.data['name']
        flask.session['identity']['email'] = me.data['email']
        flask.session['identity']['picture'] = me.data['picture']
        return flask.redirect(flask.url_for('admin.home'))

    @google.tokengetter
    def get_google_oauth_token():
        return flask.session.get('identity', {}).get('google_token')

    @principals.identity_loader
    def load_identity():
        devel_identity = app.config.get('DEVEL_IDENTITY')
        if devel_identity:
            identity = Identity(devel_identity)
            identity.provides.add(role.admin)
            return identity

        data = flask.session.get('identity')
        if data is not None:
            identity = Identity(data['email'])
            if data['email'] in app.config.get('ADMIN_EMAILS'):
                identity.provides.add(role.admin)
            return identity

    app.register_blueprint(admin)


@admin.route('/admin')
def home():
    if not perm.admin.can():
        return flask.redirect(flask.url_for('login'))

    return flask.render_template('admin_index.html')
