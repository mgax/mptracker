import pytest
import flask


@pytest.fixture
def app():
    from mptracker.common import common
    app = flask.Flask('__main__')
    app.register_blueprint(common)
    @app.route('/foo/<uuid:the_uuid>')
    def foo(the_uuid):
        return repr([type(the_uuid), the_uuid])
    return app


def test_good_uuid_url(app):
    client = app.test_client()
    resp = client.get('/foo/8889830f-b46e-4531-a8d1-5d9be524d192')
    assert resp.status_code == 200
    assert (resp.data.decode('ascii') ==
            "[<class 'str'>, '8889830f-b46e-4531-a8d1-5d9be524d192']")


def test_bad_uuid_url(app):
    client = app.test_client()
    assert client.get('/foo/bar').status_code == 404
