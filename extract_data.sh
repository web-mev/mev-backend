#!/bin/bash

# print commands and their expanded arguments
set -x

# Immediately fail if anything goes wrong
set -e

############################################################################

# Command-line args go here

# Provide the name of the database instance as the first arg:
# This is the name that google gives to the database instance, NOT
# the actual database holding the data
DB_ID=$1

# Pass the name of the database (which is given as part of the terraform vars)
# as the second arg:
DB_NAME=$2

# The gcp zone where everything is deployed
GCP_ZONE=$3

# The name of the GCP compute instance hosting the application
COMPUTE_INSTANCE=$4

# The name of the storage bucket where the API stores files
# Do NOT include the "gs//" prefix
API_STORAGE_BUCKET=$5

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

# Copy the operations folder from the VM
gcloud compute ssh \
    --zone $GCP_ZONE \
    $COMPUTE_INSTANCE \
    --command "cd /opt/software/mev-backend/mev && gsutil -mq cp -r ./operations $BUCKET"

# Copy the storage bucket's user_resources folder:
gsutil -qm cp -r gs://$API_STORAGE_BUCKET/user_resources $BUCKET 

echo "Extracted data is available at:"
echo $BUCKET