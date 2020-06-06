#!/bin/bash

# This script manages the various services that need to be run on
# startup of the container.

# First we need to setup the database server and create a database to use
echo $PGPASSWORD > /tmp/pwd.txt
/usr/lib/postgresql/12/bin/initdb -D $HOME/postgres_data -A md5 --pwfile /tmp/pwd.txt $USER
export PG_SOCKET_DIR=$HOME/postgres
mkdir $PG_SOCKET_DIR
/usr/lib/postgresql/12/bin/pg_ctl -D $HOME/postgres_data -o "-F -p $DB_PORT -k $PG_SOCKET_DIR" -w start
/usr/lib/postgresql/12/bin/createdb -h localhost -p $DB_PORT $DB_NAME
/usr/lib/postgresql/12/bin/psql -h localhost -p $DB_PORT -c "CREATE USER $DB_USER PASSWORD '$DB_PASSWD';" $DB_NAME
/usr/lib/postgresql/12/bin/psql -h localhost -p $DB_PORT -c "ALTER USER $DB_USER CREATEDB;" $DB_NAME

# Create directories that Django will use for uploaded files, etc.
mkdir /www/pending_user_uploads
mkdir /www/user_resources

# Specify the appropriate settings file:
if [ $ENVIRONMENT = 'dev' ]; then
    export DJANGO_SETTINGS_MODULE=mev.settings_dev
else
    export DJANGO_SETTINGS_MODULE=mev.settings_production
fi

# Apply database migrations, collect the static files to server, and create
# a superuser based on the environment variables passed to the container.
python3 /www/manage.py makemigrations api
python3 /www/manage.py migrate
python3 /www/manage.py collectstatic --noinput
python3 /www/manage.py createsuperuser --noinput

# Populate a "test" database, so the database
# will have some content to query.
if [ $POPULATE_DB = 'yes' ]; then
    python3 /www/manage.py populate_db
fi

# Startup redis and celery
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread && supervisorctl update

# Start the application server:
cd /www
gunicorn mev.wsgi:application $@




