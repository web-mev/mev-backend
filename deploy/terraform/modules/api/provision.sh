#!/usr/bin/env bash

# print commands and their expanded arguments
set -x

set -o allexport
CROMWELL_IP=${cromwell_ip}
set +o allexport


echo $CROMWELL_IP > /var/test.txt

echo "DONE"