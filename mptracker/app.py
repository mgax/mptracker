import flask


def create_app():
    app = flask.Flask(__name__)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
