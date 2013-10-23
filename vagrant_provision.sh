#!/bin/bash

POSTGRES_KEY_URL='http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc'
POSTGRES_REPO='deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main'
VIRTUALENV_PY='https://raw.github.com/pypa/virtualenv/develop/virtualenv.py'
SETUPTOOLS_URL='https://pypi.python.org/packages/source/s/setuptools/setuptools-1.1.6.tar.gz'
PIP_URL='https://pypi.python.org/packages/source/p/pip/pip-1.4.1.tar.gz'

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo apt-get install -y curl python-software-properties
sudo curl "$POSTGRES_KEY_URL" | sudo apt-key add -
sudo add-apt-repository -y "$POSTGRES_REPO"
sudo add-apt-repository -y ppa:fkrull/deadsnakes
sudo apt-get update
sudo apt-get install -y postgresql-9.3 postgresql-contrib-9.3 \
                        postgresql-server-dev-9.3 \
                        build-essential libxml2-dev libxslt1-dev \
                        python3.3 python3.3-dev git vim

sudo -u postgres psql -c "CREATE USER mptracker WITH ENCRYPTED PASSWORD 'mptracker';"
sudo -u postgres psql -c "CREATE DATABASE mptracker"
sudo -u postgres psql mptracker -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'

cd /home/vagrant
if [ ! -d py33env ]; then
    echo "Creating virtualenv ..."
    curl -O "$VIRTUALENV_PY"
    curl -O "$SETUPTOOLS_URL"
    curl -O "$PIP_URL"
    python virtualenv.py -p python3.3 py33env
    grep py33env .bashrc ||  echo "source ~/py33env/bin/activate" >> .bashrc
fi

cd /vagrant

~/py33env/bin/pip install -r requirements-dev.txt

if [ ! -f settings.py ]; then
    echo "Creating configuration file ..."
    DB_URI='postgresql://mptracker:mptracker@localhost:5432/mptracker'
    echo "DEBUG = True" >> settings.py
    echo "SECRET_KEY = 'foo'" >> settings.py
    echo "SQLALCHEMY_DATABASE_URI = '$DB_URI'" >> settings.py
fi

~/py33env/bin/python manage.py db sync
