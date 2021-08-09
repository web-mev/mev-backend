#! /bin/bash

# Immediately fail if anything goes wrong.
set -e

# print commands and their expanded arguments
set -x

#################### Start ENV variables #################################
# This section contains environment variables that are populated
# by terraform as part of its templatefile function

set -o allexport

source /vagrant/$1

DATA_DIR=/data

set +o allexport

#################### End ENV variables #################################

# create the mev user and add them to the docker group
# so they are able to execute Docker containers
addgroup --system mev && adduser --system --group mev
usermod -aG docker mev

# Create a directory where we will download/install our software
mkdir /opt/software

# Install redis
cd /opt/software && \
  wget https://download.redis.io/releases/redis-6.2.1.tar.gz
  tar -xzf redis-6.2.1.tar.gz && \
  cd redis-6.2.1 && \
  make && \
  make install

# setup some static environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Copy the various supervisor conf files to the appropriate locations
cd /vagrant/deploy/mev/supervisor_conf_files && \
cp redis.conf /etc/supervisor/conf.d/ && \
cp celery_worker.conf /etc/supervisor/conf.d/ && \
cp celery_beat.conf /etc/supervisor/conf.d/ && \
cp gunicorn.conf /etc/supervisor/conf.d/


# Copy the nginx config file, removing the existing default
rm -f /etc/nginx/sites-enabled/default
cp /vagrant/deploy/mev/nginx.conf /etc/nginx/sites-enabled/

# Create the log directory and the dir from which nginx will
# eventually serve static files
mkdir -p /var/log/mev
mkdir -p /www

# touch some log files which will then be transferred to the mev 
# user.
touch /var/log/mev/celery_beat.log  \
  /var/log/mev/celery_worker.log  \
  /var/log/mev/cloud_sql.log  \
  /var/log/mev/gunicorn.log  \
  /var/log/mev/redis.log

# Give the mev user ownership of the code directory and the logging directory
chown -R mev:mev /var/log/mev /www
 
# use localhost when we're in dev. the postgres server is local
export DB_HOST_SOCKET=$DB_HOST_FULL

# Specify the appropriate settings file.
# We do this here so it's prior to cycling the supervisor daemon
export DJANGO_SETTINGS_MODULE=mev.settings_dev

# Generate a set of keys for signing the download URL for bucket-based files.
# Don't really need this for local dev, but it needs to be populated for the app
# to startup properly
touch $STORAGE_CREDENTIALS

# First restart supervisor since it needs access to the
# environment variables (can only read those that are defined
# when the supervisor daemon starts)
service supervisor stop
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

# Some preliminaries before we start asking django to set things up:
mkdir $DATA_DIR
mkdir -p $DATA_DIR/pending_user_uploads
mkdir -p $DATA_DIR/resource_cache
mkdir -p $DATA_DIR/operation_staging
mkdir -p $DATA_DIR/operations
mkdir -p $DATA_DIR/operation_executions

# Change the ownership so we have write permissions.
chown -R mev:mev $DATA_DIR

# Workaround to allow vagrant to write to /data. This is needed
# when running unit tests
chmod -R o+w $DATA_DIR

# Apply database migrations, collect the static files to server, and create
# a superuser based on the environment variables passed to the container.

if [ "$RESTORE_FROM_BACKUP" = "yes" ]; then

    # Check that the proper folder exists which has the backup data
    BACKUP_DIR="/vagrant/example_data"
    ls $BACKUP_DIR || (echo "Since you requested to populate the database from a backup, you must have a directory named example_data."; exit 1)

    ls $BACKUP_DIR/$BACKUP_FILE* || (echo "Did not find any database dump."; exit 1)

    # Have either a compressed or uncompressed file present. If the following `ls` for the
    # uncompressed file fails, then we need to uncompress
    ls $BACKUP_DIR/$BACKUP_FILE || gunzip $BACKUP_DIR/$BACKUP_FILE".gz" 

    # The cloud managed database adds some extra users which interfere with our setup here.
    # This first line removes the line referencing the "cloudsqladmin" user
    sed -i 's?^.*cloudsqladmin.*$??g' $BACKUP_DIR/$BACKUP_FILE

    # This next command replaces the GRANT command for the cloudsqlsuperuser
    # with the WebMeV database user. Without this, we end up with permissions
    # errors when querying the DB via Django
    sed -i "s?cloudsqlsuperuser?$DB_USER?g" $BACKUP_DIR/$BACKUP_FILE

    # If we are restoring from a backup, we fill the database with real data.
    # This also sets up the tables, etc.
    export PGPASSWORD=$DB_PASSWD
    runuser -m postgres -c "psql -v ON_ERROR_STOP=1 -h localhost --username "$DB_USER" --dbname "$DB_NAME" < $BACKUP_DIR/$BACKUP_FILE"

    # Run a script which will correct the cloud-based paths to local ones.
    # This edits the database AND moves the files
    /usr/local/bin/python3 /vagrant/mev/manage.py edit_db_data \
      --email $DJANGO_SUPERUSER_EMAIL \
      --password $DJANGO_SUPERUSER_PASSWORD \
      --dir $BACKUP_DIR/$LOCAL_STORAGE_DIRNAME

    # Also move the operations
    /usr/local/bin/python3 /vagrant/mev/manage.py move_operations \
      --dir $BACKUP_DIR"/operations" \
      --output /vagrant/mev/operations
  /usr/local/bin/python3 /vagrant/mev/manage.py migrate
  /usr/local/bin/python3 /vagrant/mev/manage.py createsuperuser --noinput || echo "User existed already"

else

  /usr/local/bin/python3 /vagrant/mev/manage.py migrate
  /usr/local/bin/python3 /vagrant/mev/manage.py createsuperuser --noinput


  # Populate a "test" database, so the database
  # will have some content to query. Note that we only do this
  # if we are not populating from a backup
  if [ "$POPULATE_DB" = "yes" ]; then
      /usr/local/bin/python3 /vagrant/mev/manage.py populate_db
  fi

fi

# The collectstatic command gets all the static files 
# and puts them at /vagrant/mev/static.
# We them copy the contents to /www/static so nginx can serve:
/usr/local/bin/python3 /vagrant/mev/manage.py collectstatic --noinput
cp -r /vagrant/mev/static /www/static

# Add on "static" operations, such as the dropbox uploaders, etc.
# Other operations (such as those used for a differential expression
# analysis) are added by admins once the application is running.
# Temporarily commented to avoid the slow build.
if [ "$ENVIRONMENT" != "dev" ]; then
  /usr/local/bin/python3 /vagrant/mev/manage.py add_static_operations
fi
# Start and wait for Redis. Redis needs to be ready before
# celery starts.
supervisorctl start redis
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 2
done
echo "Redis started!"

# Start celery:
supervisorctl start mev_celery_beat
supervisorctl start mev_celery_worker

# Restart nginx so it loads the new config:
service nginx restart

# Add to the vagrant user's ~/.profile so that the environment variables
# are "ready" after you SSH into the VM
echo "source /vagrant/vagrant/final_setup.sh /vagrant/"$1 >> /home/vagrant/.profile
