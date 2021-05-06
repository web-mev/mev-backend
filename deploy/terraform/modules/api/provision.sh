#!/usr/bin/env bash

# print commands and their expanded arguments
set -x

# Note that DB_HOST will be provided by terraform and will look like: <project>:<region>:<name>

set -o allexport

CROMWELL_IP=${cromwell_ip}
DOMAIN=${domain}
DB_USER=${db_user}
ROOT_DB_PASSWD=${root_db_passwd}
DB_PASSWD=${db_passwd}
DB_NAME=${db_name}
DB_PORT=${db_port}
DB_HOST_FULL=${db_host}
REPO=${repo}
SECRET_KEY="asdfsd8fsdfsdf3e39a2asdfdsfe33kkal"
INTERNAL_IP=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip" -H "Metadata-Flavor: Google")

set +o allexport

apt-get update
apt-get install -y \
    python3-dev \
    python3-pip \
    postgresql-12 \
    libpq-dev \
    nginx

DB_HOST=$(python3 -c "import sys,os; s=os.environ['DB_HOST_FULL']; sys.stdout.write(s.split(':')[-1])")

# Need to set a password for the default postgres user
gcloud beta sql users set-password postgres --instance=$DB_HOST --password $ROOT_DB_PASSWD

# Download the cloud SQL proxy
mkdir -p /opt/software
cd /opt/software
VERSION=v1.21.0 # see Releases for other versions
wget "https://storage.googleapis.com/cloudsql-proxy/$VERSION/cloud_sql_proxy.linux.amd64" -O cloud_sql_proxy
chmod +x cloud_sql_proxy
# supervisor-ize this
./cloud_sql_proxy -instances=$DB_HOST -dir=/cloudsql

export DB_HOST_SOCKET=/cloudsql/$DB_HOST_FULL

# call the database to setup the table.
psql -v ON_ERROR_STOP=1 --host=/cloudsql/$DB_HOST_FULL --username "postgres" --dbname "postgres" --password $ROOT_DB_PASSWD <<-EOSQL
    CREATE USER "$DB_USER" WITH PASSWORD '$DB_PASSWD';
    CREATE DATABASE "$DB_NAME";
    GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
    ALTER USER "$DB_USER" CREATEDB;
EOSQL


mkdir /www
cd /www
pip3 install Django psycopg2 gunicorn
git clone $REPO src
cd src
python3 manage.py makemigrations
python3 manage.py migrate
rm /etc/nginx/sites-enabled/default
cp nginx.conf /etc/nginx/sites-enabled/
service nginx restart
gunicorn mysite.wsgi:application --bind=unix:/tmp/gunicorn.sock
echo "DONE"

