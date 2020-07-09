import os
import requests
import warnings
import logging

import google
from google.cloud import storage

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from .base import BaseStorageBackend

from api.utilities.basic_utils import make_local_directory

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

class GoogleBucketStorage(BaseStorageBackend):

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
        logger.info('Requesting bucket: {bucket_name}'.format(
            bucket_name=bucket_name))
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
                    GOOGLE_BUCKET_NAME,
                    location=region
                )
                logger.info('Bucket created.')
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
        logger.info('Start upload from {local_path} to {blob}'.format(
            local_path=local_path, 
            blob=blob
        ))
        blob.upload_from_filename(local_path)
        logger.info('Completed upload from {local_path} to {blob}'.format(
            local_path=local_path, 
            blob=blob
        ))

    def download_blob(self, blob, local_path):
        logger.info('Start download from {blob} to {local_path}'.format(
            local_path=local_path, 
            blob=blob
        ))
        blob.download_to_filename(local_path)
        logger.info('Complete download from {blob} to {local_path}'.format(
            local_path=local_path, 
            blob=blob
        ))

    def get_blob(self, path):
        '''
        Returns a google storage Blob object given the path in 
        google storage.  Should be a full path (e.g. gs://bucket/object.txt)
        '''
        logger.info('Get blob at {path}'.format(path=path))
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

        return bucket.get_blob(object_name)

    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        logger.info('Store resource {pk} in Google bucket storage'.format(
            pk=resource_instance.pk)
        )

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
        logger.info('Requesting deletion of file at {path}'.format(
            path=path
        ))
        blob = self.get_blob(path)
        try:
            blob.delete()
            logger.info('Successfully deleted file at {path}'.format(
                path=path
            ))
        except Exception as ex:
            logger.error('Failed when deleting file at {path}'.format(
                path=path
            ))

    def get_filesize(self, path):
        blob = self.get_blob(path)
        size = blob.size
        if size:
            return size
        else:
            return 0

    def get_local_resource_path(self, resource_instance):
        '''
        Returns the path to the file resource on the local machine.
        
        For this case of Google bucket-based storage, we download
        the blob to the local cache dir if it does not already exist
        there. 
        '''
        logger.info('Pulling Resource ({pk}) from google storage'
        ' to local cache.'.format(
            pk = resource_instance.pk
        )
        )
        # the path relative to the "root" of the storage backend
        relative_path = BaseStorageBackend.construct_relative_path(resource_instance)

        local_cache_location = os.path.join(
            settings.RESOURCE_CACHE_DIR,
            relative_path
        )

        # need to check that the cache directory for this user exists:
        user_cache_dir = os.path.dirname(local_cache_location)
        if not os.path.exists(user_cache_dir):
            logger.info('User cache dir did not exist.  Create it.')
            make_local_directory(user_cache_dir)

        # if the file doesn't exist in our cache, go get it
        if not os.path.exists(local_cache_location):
            logger.info('Did not locate file in local cache. Download it.')
            blob = self.get_blob(resource_instance.path)
            try:
                self.download_blob(blob, local_cache_location)
            except Exception as ex:
                logger.error('Could not complete download to local cache.'
                    ' Requested file was at {blob}.'.format(
                        blob=blob
                    )
                )
                raise ex
        else:
            logger.info('Resource was already located in the local cache.')
        return local_cache_location 

        