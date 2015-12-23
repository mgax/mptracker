#!/usr/bin/env python

from mptracker.website.app import create_website_app


app = create_website_app()

if __name__ == '__main__':
    import logging
    from flask.ext.script import Manager

    logging.basicConfig()
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    if app.config.get('SQL_DEBUG'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    manager = Manager(app)
    manager.run()
