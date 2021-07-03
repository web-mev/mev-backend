#!/bin/bash

# Source the file that was used to setup the environment variables
# for creating this virtual machine. That file comes from filling in
# env.tmpl.
set -o allexport
source $1
set +o allexport

# After exporting all those variables, we still need to export these 
# for Django's purposes. The provisioning script dynamically sets these to create
# the proper resources and setup the database (among other things), but
# we need to do it here since the SSH into the VM clears those env 
# variables set during provisioning.
# TODO: can we modify the bash profile during provisioning instead?
export DJANGO_SETTINGS_MODULE=mev.settings_dev
export DB_HOST_SOCKET=$DB_HOST_FULL
export MEV_HOME=/vagrant/mev