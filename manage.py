#!/usr/bin/env python

from mptracker.app import create_app, create_manager


def main():
    import os
    import logging
    logging.basicConfig(loglevel=logging.DEBUG)
    app = create_app()

    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('alembic').setLevel(logging.INFO)
    if app.config.get('SQL_DEBUG'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    if app.config.get('SCRAPER_DEBUG'):
        logging.getLogger('mptracker.scraper').setLevel(logging.DEBUG)
        logging.getLogger('mptracker.patcher.TablePatcher').setLevel(logging.DEBUG)

    manager = create_manager(app)
    manager.run()


if __name__ == '__main__':
    main()
else:
    app = create_app()
