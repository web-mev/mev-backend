#! /bin/bash

# This script is used to provision and machine which runs the Cromwell server.
# We assume that you have set certain environment variables which are used for 
# configuring Cromwell for your cloud environment and for setting database params
# such as users and passwords. The required environment variables can be found
# in the deployment/cromwell/cromwell_vars.<provider>.template.txt in the src
# repository. Above, "<provider>" is specific to your cloud provider (e.g. google)

# Fill out that file with the environment variables and then pass the path to that
# file as the FIRST argument to this script.

set -x

# Ingest a file that has some environment variables that we will need later
set -o allexport
source $1
set +o allexport

# Basics
apt-get update
apt-get install -y default-jre \
    build-essential \
    apt-transport-https \
    ca-certificates \
    gnupg2 \
    software-properties-common \
    wget \
    python3-dev \
    python3-pip \
    postgresql-12 \
    supervisor


# Download cromwell and create an environment variable pointing at the jar
mkdir -p /opt/software/cromwell
wget https://github.com/broadinstitute/cromwell/releases/download/60/cromwell-60.jar \
    -P /opt/software/cromwell/
export CROMWELL_JAR=/opt/software/cromwell/cromwell-60.jar

# Add a user who will run Cromwell and add them to the docker group so they can 
# start the mysql Docker container
adduser --disabled-password --gecos "" cromwell-runner

# The default log directory for Cromwell. Give the new user ownership
mkdir /var/log/cromwell
chown cromwell-runner:cromwell-runner /var/log/cromwell

# Fill out the config files and create the database based on the environment variables.
# Jinja helps us fill in the cromwell conf file
pip3 install jinja2
python3 fill_conf.py \
    -i ./cromwell_gcp.template.conf \
    -o /opt/software/cromwell/gcp.conf

# Copy the supervisor conf files to the appropriate dir:
cp cromwell_server.supervisor.conf /etc/supervisor/conf.d/

# Ensure we can reach the database...
echo "Waiting for database..."
while ! nc -z localhost 5432; do
  sleep 1
  echo "Not ready yet..."
done
echo "Database ready!"

# Create the database
/usr/sbin/runuser -l postgres -c "psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<-EOSQL
    CREATE USER $CROMWELL_DB_USER PASSWORD '$CROMWELL_DB_PASSWORD';
    CREATE DATABASE $CROMWELL_DB_NAME;
    GRANT ALL PRIVILEGES ON DATABASE $CROMWELL_DB_NAME TO $CROMWELL_DB_USER;
    ALTER USER $CROMWELL_DB_USER CREATEDB;
    CREATE extension lo;
EOSQL
"

# Start cromwell:
# We first have to stop/restart the supervisor daemon to use its string interpolation functionality.
service supervisor stop
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl start cromwell_server
