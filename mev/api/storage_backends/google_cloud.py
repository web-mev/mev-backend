import os
import requests
import warnings
import logging

import google
from google.cloud import storage

from django.core.exceptions import ImproperlyConfigured

from .base import BaseStorageBackend

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

logger = logging.getLogger(__name__)

class GoogleBucketStore(BaseStorageBackend):

    def __init__(self):
        super().__init__()
        self.storage_client = storage.Client()

    def get_instance_region(self):
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
            
    def get_or_create_bucket(self):
        try:
            bucket = self.storage_client.get_bucket(GOOGLE_BUCKET_NAME)
        except google.api_core.exceptions.NotFound as ex:
            logger.info('Google bucket with name {bucket_name} did'
                ' not exist.  Create.'.format(
                    bucket_name = GOOGLE_BUCKET_NAME
                ))
            region = self.get_instance_region()
            try:
                bucket = storage_client.create_bucket(
                    GOOGLE_BUCKET_NAME
                    location=region
                )
            except ValueError as ex:
                logger.error('Could not create bucket.  Reason: {ex}'.format(
                    ex = ex
                ))
                raise ex
            except google.api_core.exceptions.BadRequest as ex:                
                logger.error('Could not create bucket due to bad request.'
                    '  Reason: {ex}'.format(
                    ex = ex
                ))
                raise ex
        return bucket

    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        super().store(resource_instance)

        final_url = os.path.join(GOOGLE_BUCKET_NAME, self.relative_path)

        bucket = self.get_or_create_bucket()
        #TODO finish
        base_storage_dir = os.path.join(settings.BASE_DIR, USER_STORAGE_DIRNAME)
        if not os.path.exists(base_storage_dir):

            # this function can raise an exception which will get
            # pushed up to the caller
            make_local_directory(base_storage_dir)

        # storage directory existed.  Move the file:
        destination = os.path.join(base_storage_dir, self.relative_path)
        source = resource_instance.path
        move_resource(source, destination)
        resource_instance.path = destination

        #TODO: complete implementation.

        resource_instance.path = final_url

    def delete(self, path):
        #TODO: implement
        pass

    def get_filesize(self, path):
        #TODO: implement
        pass