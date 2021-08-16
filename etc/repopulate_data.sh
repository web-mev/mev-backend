#!/bin/bash

# This script is used to pull the necessary files from a bucket to repopulate the state of a 
# WebMeV instance which we are restarting. The database is restored from backup in the 
# terraform script

# The name of the bucket where the file are held. Include the gs:// prefix
# Be sure to NOT have a trailing slash.
BUCKET=$1

# This is where the mev applicatoin is rooted 
MEV_DATA_DIR="/data"

# Copy the operation-related folders
gsutil -m cp -r $BUCKET/operations/* $MEV_DATA_DIR"/operations/"
gsutil -m cp -r $BUCKET/operation_executions/* $MEV_DATA_DIR"/operation_executions/"

# Pull the Docker images after getting the file that lists the docker images
gsutil cp $BUCKET/docker_images.txt $MEV_DATA_DIR/
sed -e 's?^?docker pull ?g' $MEV_DATA_DIR/docker_images.txt >$MEV_DATA_DIR/pull_docker_images.sh
bash $MEV_DATA_DIR/pull_docker_images.sh
