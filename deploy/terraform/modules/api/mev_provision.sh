#! /bin/bash

# https://serverfault.com/a/670688
export DEBIAN_FRONTEND=noninteractive
# Immediately fail if anything goes wrong
set -e
# print commands and their expanded arguments
set -x

#################### Start ENV variables #################################
# This section contains environment variables that are populated
# by terraform as part of its templatefile function

set -o allexport

# dev or production status. Should be "dev" or "production"
FACTER_ENVIRONMENT=${environment}

# Specify the appropriate settings file.
# We do this here so it's prior to cycling the supervisor daemon
if [ $FACTER_ENVIRONMENT = 'dev' ]; then
    FACTER_DJANGO_SETTINGS_MODULE=mev.settings_dev
else
    FACTER_DJANGO_SETTINGS_MODULE=mev.settings_production
fi

# temp workaround required for Celery
DJANGO_SETTINGS_MODULE=$FACTER_DJANGO_SETTINGS_MODULE

###################### Git-related parameters ###########################################

# The commit identifier which we will deploy
GIT_COMMIT=${commit_id}

###################### END Git-related parameters ###########################################

###################### Database-related parameters ######################################

# Postgres database params
FACTER_DATABASE_NAME=${db_name}
FACTER_DATABASE_USER=${db_user}
FACTER_DATABASE_PASSWORD=${db_passwd}
ROOT_DB_PASSWD=${root_db_passwd}
FACTER_DATABASE_PORT=${db_port}

# Note that the db_host is given as <project>:<region>:<db name>
# To use in Django, we eventually split this string to extract
# what we need
DB_HOST_FULL=${db_host}

CLOUD_SQL_MOUNT=/cloudsql
FACTER_DATABASE_HOST_SOCKET=$CLOUD_SQL_MOUNT/$DB_HOST_FULL

# Should we populate the database with dummy data (the same data we test with)?
# Enter "yes" (case-sensitive, without quotes) if so.  Otherwise, it will NOT populate the db
POPULATE_DB=no

###################### END Database-related parameters ###################################


############################ Domain parameters ######################################

# The frontend can be located on a different server.
# This is used for communications, etc. (such as verification emails)
# which will direct the user to a link on the front-end
FACTER_FRONTEND_DOMAIN=${frontend_domain}

# The domain of the API:
FACTER_BACKEND_DOMAIN=${domain}

########################## END Domain parameters #####################################


######################### Django-related parameters ######################################


# The secret key is used to encrypt data when making tokens, etc.
# Accordingly, make this appropriately long:
FACTER_SECRET_KEY=${django_secret}

# A comma-delimited list of the hosts.  Add hosts as necessary
# e.g. 127.0.0.1,localhost,xx.xxx.xx.xx,mydomain.com
# Also need to add the network internal IP, which we can query from the metadata
INTERNAL_IP=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip" -H "Metadata-Flavor: Google")

LOAD_BALANCER_IP=${load_balancer_ip}
DJANGO_ALLOWED_HOSTS=$FACTER_BACKEND_DOMAIN,$INTERNAL_IP,$LOAD_BALANCER_IP

# A comma-delimited list of the origins for cors requests
# Needed to hookup to front-end frameworks which may be 
# at a different domain. Include protocol and ports
DJANGO_CORS_ORIGINS=https://$FACTER_FRONTEND_DOMAIN,${other_cors_origins}


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





###################### Start cloud env related parameters ###############################


# Here we setup some parameters relating to the cloud environment, including the location
# of remote job runner services, etc.

# Will you be using one of the remote job runners?
# Case-sensitive "yes" (without quotes) will enable. Otherwise we will
# not enable remote job runs
FACTER_ENABLE_REMOTE_JOB_RUNNERS=${enable_remote_job_runners}

# Which remote job runners will be used?
# Doesn't matter if the ENABLE_REMOTE_JOB_RUNNERS is "false"
# This is a comma-delimited list of strings which have to match
# the recognized keys (see AVAILABLE_REMOTE_JOB_RUNNERS in the
# Django settings file(s)).
FACTER_REMOTE_JOB_RUNNERS=${remote_job_runners}


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
FACTER_STORAGE_LOCATION=${storage_location}

# A bucket where MEV user's files will be stored (if using bucket storage). 
# The variable passed has the prefix since it was created by terraform.
# ultimately, we DO NOT inlude the prefix, e.g. "gs://" or "s3://".
STORAGE_BUCKET_NAME_W_PREFIX=${mev_storage_bucket}
FACTER_STORAGE_BUCKET_NAME=$(python3 -c "import os,sys; x=os.environ['STORAGE_BUCKET_NAME_W_PREFIX'];sys.stdout.write(x[5:])")

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




############################ Sentry parameters ######################################

# After starting the sentry instance, tell it to configure for Django.  When you do 
# that, it will give a code snippet.  Note the "dsn" it provides, which is a URL
# that typically looks like http://<string>@<ip>:<port>/1
# Copy that url below (including the http/https prefix)
FACTER_SENTRY_URL=${sentry_url}

########################## END Sentry parameters #####################################





############################ Dockerhub related parameters ######################################

# To push to the Dockerhub repository, we need to authenticate with `docker login`...
# These credentials are used for that.

FACTER_DOCKERHUB_USERNAME=${dockerhub_username}
FACTER_DOCKERHUB_PASSWORD=${dockerhub_passwd}

# If we wish to associate the images with an organization account, specify this variable.
# If not given (i.e. empty string), then images will be pushed to the username given above.
FACTER_DOCKERHUB_ORG=${dockerhub_org}

############################ END Dockerhub related parameters ######################################


########################## Cromwell parameters #########################################
# Only need to fill-in variables here if you are using the remote Cromwell job engine
# This is only relevant if ENABLE_REMOTE_JOB_RUNNERS and REMOTE_JOB_RUNNERS
# are used

# If using the Cromwell engine to run remote jobs, we need to know the bucket where it will
# write files. If NOT using Cromwell, then this does not have to be filled.
CROMWELL_BUCKET_W_PREFIX=${cromwell_bucket}
FACTER_CROMWELL_BUCKET=$(python3 -c "import os,sys; x=os.environ['CROMWELL_BUCKET_W_PREFIX'];sys.stdout.write(x[5:])")
 
# The address (including http/s protocol and any port) of the Cromwell server
# Only needed if using the remote Cromwell job engine.
# Should be the INTERNAL IP address in the same vpc network
FACTER_CROMWELL_SERVER_URL=http://${cromwell_ip}:8000

########################## END Cromwell parameters #########################################

FACTER_DATA_DIR=/data
MEV_USER=ubuntu

set +o allexport

#################### End ENV variables #################################

# Create a directory where we will download/install our software
mkdir /opt/software

# Get the MEV backend source
cd /opt/software && \
  git clone https://github.com/web-mev/mev-backend.git && \
  cd mev-backend && \
  git checkout -q $GIT_COMMIT

# install Puppet
CODENAME=$(/usr/bin/lsb_release -sc)
/usr/bin/curl -sO "https://apt.puppetlabs.com/puppet6-release-$CODENAME.deb"
/usr/bin/dpkg -i "puppet6-release-$CODENAME.deb"
/usr/bin/apt-get -qq update
/usr/bin/apt-get -qq -y install puppet-agent
# install and configure librarian-puppet
/opt/puppetlabs/puppet/bin/gem install librarian-puppet -v 3.0.1 --no-document
export HOME="/root"  # workaround for https://github.com/rodjek/librarian-puppet/issues/258
/opt/puppetlabs/puppet/bin/librarian-puppet config path /opt/puppetlabs/puppet/modules --global
/opt/puppetlabs/puppet/bin/librarian-puppet config tmp /tmp --global
# install Puppet modules
PATH="$PATH:/opt/puppetlabs/bin" && \
  cd /opt/software/mev-backend/deploy/puppet && \
  /opt/puppetlabs/puppet/bin/librarian-puppet install
/opt/puppetlabs/bin/puppet apply /opt/software/mev-backend/deploy/puppet/manifests/site.pp
unset HOME  # for Cloud SQL Proxy

# setup some static environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Copy the nginx config file, filling out the host, and removing the existing default
rm -f /etc/nginx/sites-enabled/default
sed -e "s?__SERVER_NAME__?$FACTER_BACKEND_DOMAIN?g" /opt/software/mev-backend/deploy/mev/nginx.conf > /etc/nginx/sites-enabled/nginx.conf

# Create the log directory and the dir from which nginx will
# eventually serve static files
mkdir -p /var/log/mev
mkdir -p /www

# touch some log files which will then be transferred to the mev 
# user.
touch /var/log/mev/celery_beat.log  \
  /var/log/mev/celery_worker.log  \
  /var/log/mev/cloud_sql.log  \
  /var/log/mev/gunicorn.log

# Give the mev user ownership of the code directory and the logging directory
chown -R $MEV_USER:$MEV_USER /opt/software /var/log/mev /www

  # Create the postgres database...
  # Extract the shorter database hostname from the full string. Django looks 
  # for this environment variable
  export DB_HOST=$(python3 -c "import sys,os; s=os.environ['DB_HOST_FULL']; sys.stdout.write(s.split(':')[-1])")

  # Need to set a password for the default postgres user
  gcloud beta sql users set-password postgres --instance=$DB_HOST --password $ROOT_DB_PASSWD

  # Download the cloud SQL proxy
  cd /opt/software && mkdir database && cd database
  CLOUD_SQL_PROXY_VERSION=v1.21.0
  curl -s -o cloud_sql_proxy "https://storage.googleapis.com/cloudsql-proxy/$CLOUD_SQL_PROXY_VERSION/cloud_sql_proxy.linux.amd64"
  chmod +x cloud_sql_proxy

  mkdir $CLOUD_SQL_MOUNT
  chown -R $MEV_USER:$MEV_USER $CLOUD_SQL_MOUNT


# the path to a JSON file containing the credentials to authenticate with the Google storage API.
# The startup script will perform the authentication and place the credentials into this file.
FACTER_STORAGE_CREDENTIALS="/opt/software/mev-backend/storage_credentials.json"
# Generate a set of keys for signing the download URL for bucket-based files.
gcloud iam service-accounts keys create $FACTER_STORAGE_CREDENTIALS --iam-account=$SERVICE_ACCOUNT
chown $MEV_USER:$MEV_USER $FACTER_STORAGE_CREDENTIALS

# First restart supervisor since it needs access to the
# environment variables (can only read those that are defined
# when the supervisor daemon starts)
service supervisor stop
mkdir /tmp/supervisor
chown $MEV_USER:$MEV_USER /tmp/supervisor
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread
supervisorctl start cloud_sql_proxy

# Give it some time to setup the socket to the db
sleep 10

# Setup the database if it does not exist
export PGPASSWORD=$ROOT_DB_PASSWD

if psql -lqt --host=$FACTER_DATABASE_HOST_SOCKET --username "postgres" | cut -d \| -f1 | grep -qw $FACTER_DATABASE_NAME; then
  echo "Database already existed."
  export DB_EXISTED=1
else
  echo "Create the database."
psql -v ON_ERROR_STOP=1 --host=$FACTER_DATABASE_HOST_SOCKET --username "postgres" --dbname "postgres" <<-EOSQL
    CREATE USER "$FACTER_DATABASE_USER" WITH PASSWORD '$FACTER_DATABASE_PASSWORD';
    CREATE DATABASE "$FACTER_DATABASE_NAME";
    GRANT ALL PRIVILEGES ON DATABASE "$FACTER_DATABASE_NAME" TO "$FACTER_DATABASE_USER";
    ALTER USER "$FACTER_DATABASE_USER" CREATEDB;
EOSQL
  export DB_EXISTED=0
fi

# Some preliminaries before we start asking django to set things up:
mkdir $FACTER_DATA_DIR
mkdir -p $FACTER_DATA_DIR/pending_user_uploads
mkdir -p $FACTER_DATA_DIR/resource_cache
mkdir -p $FACTER_DATA_DIR/operation_staging
mkdir -p $FACTER_DATA_DIR/operations
mkdir -p $FACTER_DATA_DIR/operation_executions
mkdir -p $FACTER_DATA_DIR/public_data

# Change the ownership so we have write permissions.
chown -R $MEV_USER:$MEV_USER $FACTER_DATA_DIR
chown -R $MEV_USER:$MEV_USER /opt/software/mev-backend/mev

# Apply database migrations, collect the static files to server, and create
# a superuser based on the environment variables passed to the container.
/usr/bin/python3 /opt/software/mev-backend/mev/manage.py migrate

if [ $DB_EXISTED == 1 ]; then
  echo "Since the DB existed, skip the creation of the Django superuser."
else
  echo "Since the DB did not exist, create the Django superuser."
  /usr/bin/python3 /opt/software/mev-backend/mev/manage.py createsuperuser --noinput
fi

# The collectstatic command gets all the static files 
# and puts them at /opt/software/mev-backend/mev/static.
# We them copy the contents to /www/static so nginx can serve:
/usr/bin/python3 /opt/software/mev-backend/mev/manage.py collectstatic --noinput
cp -r /opt/software/mev-backend/mev/static /www/static

# Populate a "test" database, so the database
# will have some content to query.
if [ $POPULATE_DB = 'yes' ]; then
    /usr/bin/python3 /opt/software/mev-backend/mev/manage.py populate_db
fi

# Add on "static" operations, such as the dropbox uploaders, etc.
# Other operations (such as those used for a differential expression
# analysis) are added by admins once the application is running.
/usr/bin/python3 /opt/software/mev-backend/mev/manage.py add_static_operations
chown -R $MEV_USER:$MEV_USER $FACTER_DATA_DIR/operations

# Start celery:
supervisorctl start mev_celery_beat
supervisorctl start mev_celery_worker

# Restart nginx so it loads the new config:
service nginx restart

# Startup the application server:
supervisorctl start gunicorn

env > /data/env_vars.txt
chown $MEV_USER:$MEV_USER /data/env_vars.txt
