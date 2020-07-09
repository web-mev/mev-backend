import os
import requests
import warnings
import logging

import google
from google.cloud import storage

from django.core.exceptions import ImproperlyConfigured

from .base import BaseStorageBackend

# Look for the necessary environment variables here-- when the application
# starts, failure to find these environment variables will cause the application
# startup to fail.
try:
    GOOGLE_BUCKET_NAME = os.environ['GOOGLE_BUCKET_NAME']
except KeyError as ex:
    raise ImproperlyConfigured('Need to supply the following environment'
        ' variable: {k}'.format(k=ex))

try:
    GOOGLE_BUCKET_REGION = os.environ['GOOGLE_BUCKET_REGION']
except KeyError as ex:
    warnings.warn('Since you have not specified a region for your storage bucket,'
        ' we will assume it is located in the same region as the VM.')
    GOOGLE_BUCKET_REGION = None

# the prefix for google storage buckets:
BUCKET_PREFIX = 'gs://'

logger = logging.getLogger(__name__)

class GoogleBucketStore(BaseStorageBackend):

    def __init__(self):
        super().__init__()
        self.storage_client = storage.Client()

    def _get_instance_region(self):
        if GOOGLE_BUCKET_REGION:
            return GOOGLE_BUCKET_REGION

        #TODO: write some general re-try function
        try:
            response = requests.get(
                'http://metadata/computeMetadata/v1/instance/zone', 
                headers={'Metadata-Flavor': 'Google'}
            )
            # zone_str is something like 'projects/{project ID number}/zones/us-east4-c'
            zone_str = response.text
            region = '-'.join(zone_str.split('/')[-1].split('-')[:2]) # now like us-east4
            return region
        except Exception as ex:
            # if we could not get the region of the instance, return None for the region
            # This will ultimately create a bucket that is multi-region
            return None
            
    def get_bucket(self, bucket_name):
        return self.storage_client.get_bucket(bucket_name)

    def get_or_create_bucket(self):
        try:
            bucket = self.get_bucket(GOOGLE_BUCKET_NAME)
        except google.api_core.exceptions.NotFound as ex:
            logger.info('Google bucket with name {bucket_name} did'
                ' not exist.  Create.'.format(
                    bucket_name = GOOGLE_BUCKET_NAME
                ))
            region = self._get_instance_region()
            try:
                bucket = storage_client.create_bucket(
                    GOOGLE_BUCKET_NAME
                    location=region
                )
            except ValueError as ex:
                # ValueError can be raised if the bucket name does not conform
                # to Google's bucket name requirements.
                logger.error('Could not create bucket.  Reason: {ex}'.format(
                    ex = ex
                ))
                raise ex
            except google.api_core.exceptions.BadRequest as ex:
                # These exceptions can be raised, for instance, if the zone
                # was not specified correctly or if the request was generally
                # malformed.             
                logger.error('Could not create bucket due to bad request.'
                    '  Reason: {ex}'.format(
                    ex = ex
                ))
                raise ex
        return bucket

    def upload_blob(self, blob, local_path):
        blob.upload_from_filename(local_path)


    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        relative_path = BaseStorageBackend.construct_relative_path(resource_instance)

        bucket = self.get_or_create_bucket()

        blob = storage.Blob(relative_path, bucket)

        try:
            self.upload_blob(blob, resource_instance.path)

            # the final path in bucket storage:
            return os.path.join(
                BUCKET_PREFIX, GOOGLE_BUCKET_NAME, relative_path)
        except Exception as ex:
            logger.error('Failed to upload to bucket.  File will'
                ' remain local on the server at path: {path}'.format(
                    path=resource_instance.path
                )
            )
            return resource_instance.path
            
    def delete(self, path):
        #TODO: implement
        pass

    def get_filesize(self, path):
        path_contents = path[len(BUCKET_PREFIX):].split('/')
        bucket_name = path_contents[0]
        object_name = '/'.join(path_contents[1:])
        try:
            bucket = self.get_bucket(bucket_name)
        except google.api_core.exceptions.NotFound as ex:
            logger.error('When requesting size of Resource located at'
                '{path}, the bucket with name {bucket_name} did'
                ' not exist.'.format(
                    path=path,
                    bucket_name = bucket_name
                ))
            raise ex

        blob = bucket.get_blob(object_name)
        size = blob.size
        if size:
            return size
        else:
            return 0