#!/bin/bash -x

# This script cleans up the bucket contents such that `terraform destroy`
# will complete without errors due to existing objects

WORKSPACE=$1

aws s3 rm --recursive s3://$WORKSPACE-webmev-storage/
aws s3 rm --recursive s3://$WORKSPACE-webmev-globus/
aws s3 rm --recursive s3://$WORKSPACE-cromwell-storage/
aws s3 rm --recursive s3://$WORKSPACE-webmev-backend-logs/
