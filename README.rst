===========================
MP Tracker, Openpolitics.ro
===========================

http://firenze.grep.ro/

A database of Romanian MPs and their activity. It crawls the `Chamber of
Deputies website`_ and extracts questions submitted by MPs.

.. _Chamber of Deputies website: http://www.cdep.ro/


Getting started
===============


The easy way, using Vagrant
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Download and install vagrant_.

2. Set up the virtual machine. This will take a while and download
   several hundred MBs of images and packages::

    $ vagrant up

3. Log into the machine and start the app. It will be accessible at
http://localhost:5001/ (vagrant takes care of mapping port 5000 in the
VM to port 5001 on the host computer)::

    $ vagrant ssh
    $ cd /vagrant
    $ ./manage.py runserver -t 0.0.0.0

4. Load a database dump. Copy the archive to the repository root, then
import it::

    $ zcat /vagrant/mptracker-yyyy-mm-dd.sql.gz | psql mptracker

.. _vagrant: http://www.vagrantup.com/


The hard way, by hand
~~~~~~~~~~~~~~~~~~~~~
Requirements:

* Python 3.3
* PostgreSQL 9.3 (debian/ubuntu: https://wiki.postgresql.org/wiki/Apt )
* libxml, libxslt (debian/ubuntu: ``apt-get install libxml2-dev libxslt-dev``)

Install dependencies (consider using virtualenv_, it makes life easier
when working with multiple projects)::

    $ pip install -r requirements-dev.txt

Configure the application. Here's a sample ``settings.py`` (it should be
in the same folder as ``manage.py``)::

    DEBUG = True
    SECRET_KEY = 'foo'
    SQLALCHEMY_DATABASE_URI = 'postgresql:///mptracker'

Set up the database::

    $ createdb mptracker
    $ ./manage.py db sync

Run the application::

    $ ./manage.py runserver


.. _virtualenv: http://www.virtualenv.org/
