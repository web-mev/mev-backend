#! /bin/bash

# Immediately fail if anything goes wrong.
set -e

# print commands and their expanded arguments
set -x

#################### Start ENV variables #################################
# This section contains environment variables that are populated
# by terraform as part of its templatefile function

set -o allexport

# dev or production status. Should be "dev" or "production"
ENVIRONMENT=${environment}

###################### Database-related parameters ######################################

# Postgres database params
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWD=${db_passwd}
ROOT_DB_PASSWD=${root_db_passwd}
DB_PORT=${db_port}

# Note that the db_host is given as <project>:<region>:<db name>
# To use in Django, we eventually split this string to extract
# what we need
DB_HOST_FULL=${db_host}

# Should we populate the database with dummy data (the same data we test with)?
# Enter "yes" (case-sensitive, without quotes) if so.  Otherwise, it will NOT populate the db
POPULATE_DB=no


###################### END Database-related parameters ###################################


############################ Domain parameters ######################################

# The frontend can be located on a different server.
# This is used for communications, etc. (such as verification emails)
# which will direct the user to a link on the front-end
FRONTEND_DOMAIN=${frontend_domain}

# The domain of the API:
BACKEND_DOMAIN=${domain}

# This setting gives a "human readable" name to the site for contacts
# For instance, could be "WebMEV" or other so that emails will have a subject
# like "Registration details for WebMEV"
SITE_NAME="WebMeV"

########################## END Domain parameters #####################################


######################### Django-related parameters ######################################


# The secret key is used to encrypt data when making tokens, etc.
# Accordingly, make this appropriately long:
DJANGO_SECRET_KEY=${django_secret}

# A comma-delimited list of the hosts.  Add hosts as necessary
# e.g. 127.0.0.1,localhost,xx.xxx.xx.xx,mydomain.com
# Also need to add the network internal IP, which we can query from the metadata
INTERNAL_IP=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip" -H "Metadata-Flavor: Google")
LOAD_BALANCER_IP=${load_balancer_ip}
DJANGO_ALLOWED_HOSTS=$BACKEND_DOMAIN,$INTERNAL_IP,$LOAD_BALANCER_IP

# A comma-delimited list of the origins for cors requests
# Needed to hookup to front-end frameworks which may be 
# at a different domain. Include protocol and ports
DJANGO_CORS_ORIGINS=https://$FRONTEND_DOMAIN,${other_cors_origins}


# For automatically creating an admin, supply the following:
# username is required, but the user model uses the email field 
# as the username.  Therefore, we auto-fill that based on the email
DJANGO_SUPERUSER_PASSWORD=${django_superuser_passwd}
DJANGO_SUPERUSER_EMAIL=${django_superuser_email}

# Don't change this:
# We use a different user model which relies on the email instead of a 
# username. However, still need to define this environment variable
# for Django's createsuperuser command to work
DJANGO_SUPERUSER_USERNAME=$DJANGO_SUPERUSER_EMAIL


####################### END Django-related parameters ###################################





####################### Redis-related parameters ###################################


# Where is redis listening?
# We assume that it is listening on the dfault port of 6379
REDIS_HOST=localhost


####################### END Redis-related parameters ###################################





###################### Start cloud env related parameters ###############################


# Here we setup some parameters relating to the cloud environment, including the location
# of remote job runner services, etc.

# The cloud platform determines which classes are used to hook up to 
# storage buckets, etc.
CLOUD_PLATFORM=GOOGLE

# Will you be using one of the remote job runners?
# Case-sensitive "yes" (without quotes) will enable. Otherwise we will
# not enable remote job runs
ENABLE_REMOTE_JOB_RUNNERS=yes

# Which remote job runners will be used?
# Doesn't matter if the ENABLE_REMOTE_JOB_RUNNERS is "false"
# This is a comma-delimited list of strings which have to match
# the recognized keys (see AVAILABLE_REMOTE_JOB_RUNNERS in the
# Django settings file(s)).
REMOTE_JOB_RUNNERS=CROMWELL


###################### END cloud env related parameters #################################





###################### Storage-related parameters ######################################


# the storage backend dictates where the "absolute" source of the files is. Of course,
# to perform many operations we need to move files back and forth between local and
# cloud storage. However, only one location serves as the "ground truth", and this is
# the path that is saved in the database (in the Resource table).
# Note that if you are requesting to use remote job runners (ENABLE_REMOTE_JOB_RUNNERS)
# then you are REQUIRED to use bucket storage. You can only use local storage if all
# your runners are local.
# Options include "local" and "remote"
STORAGE_LOCATION=remote

# If using local storage for all files (not recommended since sequencing files
# could consume large amount of disk space), set the following:
# This directory is relative to the django BASE_DIR
LOCAL_STORAGE_DIRNAME=user_resources

# A bucket where MEV user's files will be stored (if using bucket storage). This
# is independent of any buckets used as a storage location for remote job runners, etc.
# DO NOT inlude the prefix, e.g. "gs://" or "s3://".
# THIS BUCKET MUST ALREADY EXIST. 
STORAGE_BUCKET_NAME=${mev_storage_bucket}

# The maximum size (in bytes) to allow "direct" downloads from the API.
# If the file exceeds this, we ask the user to download in another way. 
# Most files are small and this will be fine. However, we don't want users
# trying to download BAM or other large files. They can do that with other methods,
# like via Dropbox.
MAX_DOWNLOAD_SIZE_BYTES=5.12e8

# For signing download URLs we need a credentials file. To create that, we need a
# service account with appropriate privileges. This variable is the full name of that
# service account file (e.g. <id>@project.iam.gserviceaccount.com)
SERVICE_ACCOUNT=${service_account_email}

###################### END Storage-related parameters ######################################

############################ Email-related parameters ######################################

# How to send email-- by default, we print emails to the console for dev
# If you would like to set another email backend (e.g. gmail), set this accordingly.
# See the docs and/or base_settings.py in the relevant section regarding email.
EMAIL_BACKEND_CHOICE=${email_backend}

# When email is sent, this will give the "from" field.  e.g. "some name <some@email.com>" (without the quotes)
FROM_EMAIL="${from_email}"

# If using Gmail for your email service, specify the following:
# See docs for how to get these values.
GMAIL_ACCESS_TOKEN=${gmail_access_token}
GMAIL_REFRESH_TOKEN=${gmail_refresh_token}
GMAIL_CLIENT_ID=${gmail_client_id}
GMAIL_CLIENT_SECRET=${gmail_client_secret}


########################## END Email-related parameters #####################################




############################ Social auth-related parameters ######################################

# a comma-delimited list giving the social auth providers to use.  Check the available
# implementations in mev/api/base_settings.py
SOCIAL_BACKENDS=GOOGLE

########################## END Social-auth-related parameters #####################################


############################ Sentry parameters ######################################

# After starting the sentry instance, tell it to configure for Django.  When you do 
# that, it will give a code snippet.  Note the "dsn" it provides, which is a URL
# that typically looks like http://<string>@<ip>:<port>/1
# Copy that url below (including the http/https prefix)
SENTRY_URL=${sentry_url}

########################## END Sentry parameters #####################################





############################ Dockerhub related parameters ######################################

# To push to the Dockerhub repository, we need to authenticate with `docker login`...
# These credentials are used for that.

DOCKERHUB_USERNAME=${dockerhub_username}
DOCKERHUB_PASSWORD=${dockerhub_passwd}

############################ END Dockerhub related parameters ######################################


########################## Cromwell parameters #########################################
# Only need to fill-in variables here if you are using the remote Cromwell job engine
# This is only relevant if ENABLE_REMOTE_JOB_RUNNERS and REMOTE_JOB_RUNNERS
# are used

# If using the Cromwell engine to run remote jobs, we need to know the bucket where it will
# write files. If NOT using Cromwell, then this does not have to be filled.
# DO NOT inlude the prefix, e.g. "gs://" or "s3://"
CROMWELL_BUCKET=${cromwell_bucket}

# The address (including http/s protocol and any port) of the Cromwell server
# Only needed if using the remote Cromwell job engine.
# Should be the INTERNAL IP address in the same vpc network
CROMWELL_SERVER_URL=http://${cromwell_ip}:8000

########################## END Cromwell parameters #########################################


set +o allexport

#################### End ENV variables #################################


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
  cd mev-backend && \
  git checkout ${branch} && \
  cd mev && \
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
  cp ./supervisor_conf_files/cloud_sql_proxy.conf /etc/supervisor/conf.d/

# Copy the nginx config file, removing the existing default
rm -f /etc/nginx/sites-enabled/default
cp nginx.conf /etc/nginx/sites-enabled/

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
chown -R mev:mev /opt/software /var/log/mev /www

# Create the postgres database...
# Extract the shorter database hostname from the full string. Django looks 
# for this environment variable
export DB_HOST=$(python3 -c "import sys,os; s=os.environ['DB_HOST_FULL']; sys.stdout.write(s.split(':')[-1])")

# Need to set a password for the default postgres user
gcloud beta sql users set-password postgres --instance=$DB_HOST --password $ROOT_DB_PASSWD

# Download the cloud SQL proxy
cd /opt/software && mkdir database && cd database
CLOUD_SQL_PROXY_VERSION=v1.21.0
wget "https://storage.googleapis.com/cloudsql-proxy/$CLOUD_SQL_PROXY_VERSION/cloud_sql_proxy.linux.amd64" -O cloud_sql_proxy
chmod +x cloud_sql_proxy

export CLOUD_SQL_MOUNT=/cloudsql
export DB_HOST_SOCKET=$CLOUD_SQL_MOUNT/$DB_HOST_FULL

# Specify the appropriate settings file.
# We do this here so it's prior to cycling the supervisor daemon
if [ $ENVIRONMENT = 'dev' ]; then
    export DJANGO_SETTINGS_MODULE=mev.settings_dev
else
    export DJANGO_SETTINGS_MODULE=mev.settings_production
fi

# Generate a set of keys for signing the download URL for bucket-base files.
export STORAGE_CREDENTIALS="/opt/software/mev-backend/storage_credentials.json"
gcloud iam service-accounts keys create $STORAGE_CREDENTIALS --iam-account=$SERVICE_ACCOUNT
chown mev:mev $STORAGE_CREDENTIALS

# First restart supervisor since it needs access to the
# environment variables (can only read those that are defined
# when the supervisor daemon starts)
service supervisor stop
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread
supervisorctl start cloud_sql_proxy

# Give it some time to setup the socket to the db
sleep 10

# Setup the database.
export PGPASSWORD=$ROOT_DB_PASSWD
psql -v ON_ERROR_STOP=1 --host=$DB_HOST_SOCKET --username "postgres" --dbname "postgres" <<-EOSQL
    CREATE USER "$DB_USER" WITH PASSWORD '$DB_PASSWD';
    CREATE DATABASE "$DB_NAME";
    GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
    ALTER USER "$DB_USER" CREATEDB;
EOSQL

# Some preliminaries before we start asking django to set things up:
mkdir -p /opt/software/mev-backend/mev/pending_user_uploads
mkdir -p /opt/software/mev-backend/mev/resource_cache
mkdir -p /opt/software/mev-backend/mev/operation_staging
mkdir -p /opt/software/mev-backend/mev/operations
mkdir -p /opt/software/mev-backend/mev/operation_executions

# Change the ownership so we have write permissions.
chown -R mev:mev /opt/software/mev-backend/mev

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

# Restart nginx so it loads the new config:
service nginx restart

# Startup the application server:
supervisorctl start gunicorn