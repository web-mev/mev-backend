#! /bin/bash

# Immediately fail if anything goes wrong.
set -e

# print commands and their expanded arguments
set -x

# Ingest a file that has environment variables that we will need later
# The path to this file is given as the first argument to the script
set -o allexport
source $1
set +o allexport

# Install some dependencies
apt-get update \
    && apt-get install -y \
    build-essential \
    apt-transport-https \
    ca-certificates \
    gnupg2 \
    software-properties-common \
    zlib1g-dev \
    libssl-dev \
    libncurses5-dev \
    libreadline-dev \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libsqlite3-dev \
    libpq-dev \
    wget \
    supervisor \
    nano \
    git \
    curl \
    pkg-config \
    netcat \
    procps \
    postgresql-12 \
    python3-pip \
    nginx \
    docker.io

# create the mev user and add them to the docker group
# so they are able to execute Docker containers
addgroup --system mev && adduser --system --group mev
usermod -aG docker mev

# Create a directory where we will download/install our software
mkdir /opt/software

# Install Python 3.7.6. Ends up in /usr/local/bin/python3
cd /opt/software && \
  wget https://www.python.org/ftp/python/3.7.6/Python-3.7.6.tgz && \
  tar -xzf Python-3.7.6.tgz && \
  cd Python-3.7.6 && \
  ./configure && \
  make && \
  make install

# Install redis
cd /opt/software && \
  wget https://download.redis.io/releases/redis-6.2.1.tar.gz
  tar -xzf redis-6.2.1.tar.gz && \
  cd redis-6.2.1 && \
  make && \
  make install

# Get the MEV backend source and install the python packages:
cd /opt/software && \
  git clone https://github.com/web-mev/mev-backend.git && \
  cd mev-backend/mev && \
  /usr/local/bin/pip3 install -U pip && \
  /usr/local/bin/pip3 install --no-cache-dir -r ./requirements.txt

# setup some static environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Copy the various supervisor conf files to the appropriate locations
# remove the following comment once we have integrated into the main project.
# The location of the supervisor conf files will change once we have done that.
cd /opt/software/mev-backend/deploy/mev/ && \
  cp ./supervisor_conf_files/redis.conf /etc/supervisor/conf.d/ && \
  cp ./supervisor_conf_files/celery_worker.conf /etc/supervisor/conf.d/ && \
  cp ./supervisor_conf_files/celery_beat.conf /etc/supervisor/conf.d/ && \
  cp ./supervisor_conf_files/gunicorn.conf /etc/supervisor/conf.d/

# Copy the nginx config file, removing the existing default
rm -f /etc/nginx/sites-enabled/default
cp nginx.conf /etc/nginx/sites-enabled/

# Create the log directory and the dir from which nginx will
# eventually serve static files
mkdir -p /var/log/mev
mkdir -p /www

# Give the mev user ownership of the code directory and the logging directory
chown -R mev:mev /opt/software /var/log/mev /www

# Ensure we can reach the postgres database...
echo "Waiting for database..."
while ! nc -z localhost 5432; do
  sleep 1
  echo "Database not ready yet..."
done
echo "Database ready!"

# Create the local database. This will eventually be moved to a
# managed cloud service
/usr/sbin/runuser -l postgres -c "psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<-EOSQL
    CREATE USER $MEV_DB_USER PASSWORD '$MEV_DB_PASSWORD';
    CREATE DATABASE $MEV_DB_NAME;
    GRANT ALL PRIVILEGES ON DATABASE $MEV_DB_NAME TO $MEV_DB_USER;
    ALTER USER $MEV_DB_USER CREATEDB;
EOSQL
"

# Specify the appropriate settings file:
if [ $ENVIRONMENT = 'dev' ]; then
    export DJANGO_SETTINGS_MODULE=mev.settings_dev
else
    export DJANGO_SETTINGS_MODULE=mev.settings_production
fi

# Some preliminaries before we start asking django to set things up:
mkdir -p /opt/software/mev-backend/mev/pending_user_uploads
mkdir -p /opt/software/mev-backend/mev/resource_cache
mkdir -p /opt/software/mev-backend/mev/operation_staging
mkdir -p /opt/software/mev-backend/mev/operations
mkdir -p /opt/software/mev-backend/mev/operation_executions

# Apply database migrations, collect the static files to server, and create
# a superuser based on the environment variables passed to the container.
/usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py makemigrations api
/usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py migrate
/usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py createsuperuser --noinput

# The collectstatic command gets all the static files 
# and puts them at /opt/software/mev-backend/mev/static.
# We them copy the contents to /www/static so nginx can serve:
/usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py collectstatic --noinput
cp -r /opt/software/mev-backend/mev/static /www/static

# Populate a "test" database, so the database
# will have some content to query.
if [ $POPULATE_DB = 'yes' ]; then
    /usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py populate_db
fi

# Add on "static" operations, such as the dropbox uploaders, etc.
# Other operations (such as those used for a differential expression
# analysis) are added by admins once the application is running.
# Temporarily commented to avoid the slow build.
#/usr/local/bin/python3 /opt/software/mev-backend/mev/manage.py add_static_operations

# Startup redis and celery. First restart supervisor just in case it needs
# any environment variables (usually can only read those that are defined
# when the supervisor daemon starts)
service supervisor stop
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread

# Start and wait for Redis. Redis needs to be ready before
# celery starts.
supervisorctl start redis
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST 6379; do
  sleep 1
done
echo "Redis started!"

# Start celery:
supervisorctl start mev_celery_beat
supervisorctl start mev_celery_worker

# Startup the application server:
supervisorctl start gunicorn