#!/bin/bash -ex

POSTGRES_KEY_URL='http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc'
POSTGRES_REPO='deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main'
VIRTUALENV_PY='https://raw.github.com/pypa/virtualenv/1.10.1/virtualenv.py'
SETUPTOOLS_URL='https://pypi.python.org/packages/source/s/setuptools/setuptools-1.1.6.tar.gz'
PIP_URL='https://pypi.python.org/packages/source/p/pip/pip-1.4.1.tar.gz'

sudo apt-get update
sudo apt-get install -y curl
sudo curl "$POSTGRES_KEY_URL" | sudo apt-key add -
sudo add-apt-repository -y "$POSTGRES_REPO"
sudo apt-get update
sudo apt-get install -y postgresql-9.3 postgresql-contrib-9.3 \
                        postgresql-server-dev-9.3 \
                        build-essential libxml2-dev libxslt1-dev \
                        python3-dev git vim virtualenv

sudo sed -e 's/^\(local .*\) peer$/\1 trust/' -i /etc/postgresql/9.3/main/pg_hba.conf
sudo service postgresql restart

grep PGUSER .bashrc ||  echo "export PGUSER='mptracker'" >> .bashrc
sudo -u postgres psql -c "CREATE USER mptracker WITH ENCRYPTED PASSWORD 'mptracker' SUPERUSER;"
createdb mptracker -U mptracker -E UTF8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8 -T template0
psql mptracker -U mptracker -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'

cd /home/vagrant
if [ ! -d venv ]; then
    echo "Creating virtualenv ..."
    curl -O "$VIRTUALENV_PY"
    curl -O "$SETUPTOOLS_URL"
    curl -O "$PIP_URL"
    virtualenv -p python3 venv
    grep venv .bashrc ||  echo "source ~/venv/bin/activate" >> .bashrc
fi

cd /vagrant

~/venv/bin/pip install -r requirements-dev.txt

if [ ! -f settings.py ]; then
    echo "Creating configuration file ..."
    DB_URI='postgresql://mptracker:mptracker@localhost:5432/mptracker'
    echo "DEBUG = True" >> settings.py
    echo "SECRET_KEY = 'foo'" >> settings.py
    echo "SQLALCHEMY_DATABASE_URI = '$DB_URI'" >> settings.py
fi
