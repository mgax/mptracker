#!/usr/bin/env python

from mptracker.app import create_app, create_manager


def main():
    import os
    import logging
    logging.basicConfig(loglevel=logging.INFO)
    app = create_app()

    logging.getLogger('werkzeug').setLevel(logging.INFO)
    if app.config.get('SQL_DEBUG'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    manager = create_manager(app)
    manager.run()


if __name__ == '__main__':
    main()
else:
    app = create_app()
