===========================
MP Tracker, Openpolitics.ro
===========================

http://firenze.grep.ro/

A database of Romanian MPs and their activity. It crawls the `Chamber of
Deputies website`_ and extracts questions submitted by MPs.

.. _Chamber of Deputies website: http://www.cdep.ro/


Getting started
===============

Requirements:

* Python 3.3
* PostgreSQL

Install dependencies (consider using virtualenv_, it makes life easier
when working with multiple projects)::

    $ pip install -r requirements-dev.txt

Configure the application. Here's a sample ``settings.py`` (it should be
in the same folder as ``manage.py``)::

    DEBUG = True
    SECRET_KEY = 'foo'
    DATABASE = 'postgresql:///mptracker'

Set up the database::

    $ createdb mptracker
    $ ./manage.py db sync

Run the application::

    $ ./manage.py runserver


.. _virtualenv: http://www.virtualenv.org/

Possibly outdated installation instructions on a fresh Debian Wheezy
box: https://gist.github.com/mgax/0d460307aa40d8021c3c
