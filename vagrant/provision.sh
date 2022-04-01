#! /bin/bash

# Immediately fail if anything goes wrong.
set -e

# print commands and their expanded arguments
set -x

#################### Start ENV variables #################################
# The /vagrant/.env file is populated by puppet
# The /vagrant/$1 arg is a file of environment variables
# Note that the .env file (populated by puppet) is itself populated by
# the env.txt file passed as $1. However, there are some vars in that file
# which we need, but don't want to put into /vagrant/.env

set -o allexport

source /vagrant/$1
source /vagrant/.env

set +o allexport


#################### End ENV variables #################################

# setup some static environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Create the dir from which nginx will eventually serve static files
mkdir -p /www

# Give the mev user ownership of the code directory and the static file directory
chown -R $MEV_USER:$MEV_USER /www

# Generate a set of keys for signing the download URL for bucket-based files.
# Don't really need this for local dev, but it needs to be populated for the app
# to startup properly
touch $STORAGE_CREDENTIALS

# First restart supervisor since it needs access to the
# environment variables (can only read those that are defined
# when the supervisor daemon starts)
service supervisor stop
mkdir /tmp/supervisor
chown $MEV_USER:$MEV_USER /tmp/supervisor
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread

# Give it some time to setup the socket to the db
sleep 3

# Setup the database. Even if we are populating from a backup, we need to 
# create the database user and database
runuser -m postgres -c "psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "postgres" <<-EOSQL
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWD';
    CREATE DATABASE $DB_NAME;
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    ALTER USER $DB_USER CREATEDB;
EOSQL"

# Apply database migrations, collect the static files to server, and create
# a superuser based on the environment variables passed to the container.
/usr/bin/python3 /vagrant/mev/manage.py migrate
/usr/bin/python3 /vagrant/mev/manage.py createsuperuser --noinput

# The collectstatic command gets all the static files 
# and puts them at /vagrant/mev/static.
# We them copy the contents to /www/static so nginx can serve:
/usr/bin/python3 /vagrant/mev/manage.py collectstatic --noinput
cp -r /vagrant/mev/static /www/static

# Add on "static" operations, such as the dropbox uploaders, etc.
# Other operations (such as those used for a differential expression
# analysis) are added by admins once the application is running.
# Temporarily commented to avoid the slow build.
if [ "$ENVIRONMENT" != "dev" ]; then
  /usr/bin/python3 /vagrant/mev/manage.py add_static_operations
fi

# Start celery:
supervisorctl start celery_beat
supervisorctl start celery_worker

# Restart nginx so it loads the new config:
service nginx restart
