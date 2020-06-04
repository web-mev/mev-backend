#!/bin/bash

# This script manages the various services that need to be run on
# startup of the container.

# We need to setup the database

# echo a pwd to the file
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


if [ $ENVIRONMENT = 'dev' ]; then
    export DJANGO_SETTINGS_MODULE=mev.settings_dev
else
    export DJANGO_SETTINGS_MODULE=mev.settings_production
fi

python3 /www/manage.py makemigrations api
python3 /www/manage.py migrate
python3 /www/manage.py collectstatic --noinput

# Startup redis, celery, gunicorn
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread && supervisorctl update

cd /wwww
gunicorn mev.wsgi:application $1




