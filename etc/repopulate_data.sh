#!/bin/bash

# This script is used to pull the necessary files from a bucket to repopulate the state of a 
# WebMeV instance which we are restarting. The database is restored elsewhere.

# The name of the bucket where the file are held. Include the gs:// prefix
# Be sure to NOT have a trailing slash.
BUCKET=$1

# This is where the mev application is rooted 
MEV_DATA_DIR="/data"

# Copy the operation-related folders
gsutil -m cp -n -r $BUCKET/operations/* $MEV_DATA_DIR"/operations/"
gsutil -m cp -n -r $BUCKET/operation_executions/* $MEV_DATA_DIR"/operation_executions/"
gsutil -m cp -n -r $BUCKET/public_data/* $MEV_DATA_DIR"/public_data/"

# Pull the Docker images after getting the file that lists the docker images
gsutil cp $BUCKET/docker_images.txt $MEV_DATA_DIR/
sed -e 's?^?docker pull ?g' $MEV_DATA_DIR/docker_images.txt >$MEV_DATA_DIR/pull_docker_images.sh
bash $MEV_DATA_DIR/pull_docker_images.sh
