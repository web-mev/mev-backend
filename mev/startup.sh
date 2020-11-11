#!/bin/bash

# This script manages the various services that need to be run on
# startup of the container.

# We have to ensure that the database server is up first...
echo "Waiting for postgres..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
  echo "Not ready yet..."
done
echo "PostgreSQL started!"

# And wait for Redis...
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 0.1
done
echo "Redis started!"

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

# Run the command, but only if in production:
if [ $ENVIRONMENT = 'dev' ]; then
    echo "Ignoring startup command.  Login to container to start gunicorn."
else
    $@
fi




