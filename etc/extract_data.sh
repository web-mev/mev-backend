#!/bin/bash

# print commands and their expanded arguments
set -x

# Immediately fail if anything goes wrong
set -e

# This script is used to preserve the server state PRIOR to a restart.
# It's intended be run on said machine


############################################################################

# Command-line args go here

# Provide the name of the database instance as the first arg:
# This is the name that Google gives to the database instance, NOT
# the actual database holding the data. This is some string like
# webmev-<environment>-db-<random>, WITHOUT any prefixes (like the GCP project or zone)
DB_ID=$1

# Pass the name of the database (which is given as part of the terraform vars)
# as the second arg:
DB_NAME=$2

# Change this as necessary. Older versions of the code may have persisted data
# at a different directory root.
DATA_DIR=/data

#############################################################################


# Create an "official" backup. This is distinct from the SQL dump that we are 
# creating below. This will be used to restore the DB. The dump file is only 
# used as a last resort.
gcloud sql backups create --instance="$DB_ID"

#############################################################################

# Create a UUID to tag a bucket:
DUMP_UUID=$(python3 -c 'import uuid; print(uuid.uuid4())')

# Create a bucket where the files will go:
BUCKET="gs://mev-data-export-$DUMP_UUID"
gsutil mb $BUCKET

# We need the service account controlling the database so that we can give
# that service account appropriate privileges to write into that new bucket.
# This gets the service account:
SVC_ACCT=$(gcloud sql instances describe $DB_ID | grep serviceAccountEmailAddress | cut -d' ' -f2)

# Now edit the bucket so that service account can write to it:
gsutil iam ch serviceAccount:$SVC_ACCT:objectAdmin $BUCKET

# Create a snapshot of the database and send it to that bucket:
gcloud sql export sql $DB_ID $BUCKET/db_export.gz --database=$DB_NAME

# This lists the current Docker images on the machine. The images are already persisted
# to Dockerhub by design, so when the server restarts, we can simply use this list to 
# pull the images
docker image ls --format "table {{.Repository}}:{{.Tag}}" \
    | grep -v "<none>:<none>" \
    | grep -v "REPOSITORY:TAG" \
    > docker_images.txt
gsutil cp docker_images.txt $BUCKET

# We need to save the operations/ and operation_executions/ directories
OPERATIONS_DIR=$DATA_DIR"/operations"
EXECUTED_OPERATIONS_DIR=$DATA_DIR"/operation_executions"
PUBLIC_DATA_DIR=$DATA_DIR"/public_data"
gsutil -m cp -r $OPERATIONS_DIR $BUCKET
gsutil -m cp -r $EXECUTED_OPERATIONS_DIR $BUCKET
gsutil -m cp -r $PUBLIC_DATA_DIR $BUCKET

echo "Files are at:"
echo $BUCKET
