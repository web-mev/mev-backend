#!/usr/bin/env bash

# print commands and their expanded arguments
set -x

set -o allexport

# Ingest a file that has some environment variables that we will need later
# The name of the Google project. Not the numeric ID
GOOGLE_PROJECT_ID="${project_id}"

# The google bucket where Cromwell will place files. Include the gs:// prefix
GOOGLE_BUCKET="${cromwell_bucket}"

# Configuration params for the postgres database. Used to setup the database AND
# configure Cromwell to connect.
CROMWELL_DB_NAME="${cromwell_db_name}"
CROMWELL_DB_USER="${cromwell_db_user}"
CROMWELL_DB_PASSWORD="${cromwell_db_password}"

# The specific git commit to deploy
GIT_COMMIT=${commit_id}

set +o allexport

# Basic installs
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

# Jinja helps us eventually fill in the cromwell conf file
pip3 install jinja2

# Download cromwell and create an environment variable pointing at the jar
mkdir -p /opt/software/cromwell
wget https://github.com/broadinstitute/cromwell/releases/download/60/cromwell-60.jar \
    -P /opt/software/cromwell/
export CROMWELL_JAR=/opt/software/cromwell/cromwell-60.jar

# Add a user who will run Cromwell
adduser --disabled-password --gecos "" cromwell-runner

# The default log directory for Cromwell. Give the new user ownership
mkdir /var/log/cromwell
chown cromwell-runner:cromwell-runner /var/log/cromwell

# Pull the WebMeV backend repo and move into the Cromwell deployment dir:
cd /opt/software
/usr/bin/git clone https://github.com/web-mev/mev-backend.git
cd mev-backend && /usr/bin/git checkout -q $GIT_COMMIT
cd deploy/cromwell || exit 1

# Fill out the config files and create the database based on the environment variables.
python3 fill_conf.py \
    -i ./cromwell_gcp.template.conf \
    -o /opt/software/cromwell/gcp.conf

# Copy the supervisor conf files to the appropriate dir:
cp cromwell_server.supervisor.conf /etc/supervisor/conf.d/

# Change ownership- was failing on permissions to write
mkdir /cromwell-workflow-logs
chown cromwell-runner:cromwell-runner /cromwell-workflow-logs

# Ensure we can reach the database...
echo "Waiting for database..."
while ! nc -z localhost 5432; do
  sleep 1
  echo "Not ready yet..."
done
echo "Database ready!"

# Create the database
/usr/sbin/runuser -l postgres -c "psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<-EOSQL
    CREATE USER \"$CROMWELL_DB_USER\" WITH PASSWORD '$CROMWELL_DB_PASSWORD';
    CREATE DATABASE \"$CROMWELL_DB_NAME\";
    GRANT ALL PRIVILEGES ON DATABASE \"$CROMWELL_DB_NAME\" TO \"$CROMWELL_DB_USER\";
    ALTER USER \"$CROMWELL_DB_USER\" CREATEDB;
    CREATE extension lo;
EOSQL
"

# Start cromwell:
# We first have to stop/restart the supervisor daemon to use its string interpolation functionality.
service supervisor stop
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl start cromwell_server
