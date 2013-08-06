#!/usr/bin/env python


def main():
    from mptracker.app import manager
    manager.run()


def log_to_stderr():
    import logging
    logging.basicConfig(loglevel=logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.INFO)


if __name__ == '__main__':
    log_to_stderr()
    main()

else:
    from mptracker.app import create_app
    app = create_app()
