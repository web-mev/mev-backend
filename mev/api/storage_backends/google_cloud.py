import os
import requests
import warnings
import logging
import backoff
import datetime

import google
from google.cloud import storage
from google.oauth2 import service_account

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from .remote_bucket import RemoteBucketStorageBackend
from api.exceptions import StorageException
from api.utilities.basic_utils import make_local_directory, get_with_retry
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)

class GoogleBucketStorage(RemoteBucketStorageBackend):

    # the prefix for google storage buckets:
    BUCKET_PREFIX = 'gs://'

    def __init__(self):
        super().__init__()
        creds = service_account.Credentials.from_service_account_file(settings.STORAGE_CREDENTIALS)
        self.storage_client = storage.Client(credentials=creds)     

    def get_bucket_region(self, bucket_name):
        '''
        Return the location/region of a bucket
        '''
        logger.info('Requesting region of bucket: {bucket_name}'.format(
                bucket_name = bucket_name
            )
        )
        bucket = self.get_bucket(bucket_name)
        loc = bucket.location
        return loc.lower()

    def get_bucket(self, bucket_name):
        logger.info('Requesting bucket: {bucket_name}'.format(
            bucket_name=bucket_name))
        try:
            return self.storage_client.get_bucket(bucket_name)
        except google.api_core.exceptions.NotFound as ex:
            logger.info('Bucket ({bucket_name}) not found. Check'
                ' that this bucket exists.'.format(bucket_name=bucket_name)
            )
            raise ex
        except google.api_core.exceptions.Forbidden as ex:
            logger.info('Did not have proper permissions to access bucket' 
                ' ({bucket_name}). Check that this bucket'
                ' exists.'.format(bucket_name=bucket_name)
            )
            raise ex
        except Exception as ex:
            logger.info('Failed to retrieve bucket ({bucket_name}) for unexpected'
                ' reason. Check that this bucket exists.'.format(bucket_name=bucket_name)
            )
            raise ex

    def get_or_create_bucket(self):
        # can't import above as we get a circular dep. issue 
        from api.cloud_backends.google_cloud import get_instance_region
        try:
            bucket = self.get_bucket(self.BUCKET_NAME)
        except google.api_core.exceptions.NotFound as ex:
            logger.info('Google bucket with name {bucket_name} did'
                ' not exist.  Create.'.format(
                    bucket_name = self.BUCKET_NAME
                ))
            region = get_instance_region()
            try:
                bucket = storage_client.create_bucket(
                    self.BUCKET_NAME,
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

    @backoff.on_exception(backoff.expo,
                      Exception,
                      max_time=600,
                      max_tries = 5)
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

        Note that this relies on the get_bucket method. Failures to get the bucket
        will raise an exception which we catch. HOWEVER, consistent with the 
        google storage sdk, failure to get the actual blob itself do NOT raise
        exceptions and instead return `None` for the blob object. We respect
        that convention here.
        '''
        logger.info('Get blob at {path}'.format(path=path))
        path_contents = path[len(self.BUCKET_PREFIX):].split('/')
        bucket_name = path_contents[0]
        object_name = '/'.join(path_contents[1:])
        try:
            bucket = self.get_bucket(bucket_name)
        except google.api_core.exceptions.NotFound as ex:
            logger.info('When requesting a blob located at'
                ' {path}, the bucket with name {bucket_name} did'
                ' not exist.'.format(
                    path=path,
                    bucket_name = bucket_name
                ))
            raise ex
        except google.api_core.exceptions.Forbidden as ex:
            logger.info('When requesting a blob located at'
                ' {path}, access to the bucket with name {bucket_name}'
                ' was not permitted (403).'.format(
                    path=path,
                    bucket_name = bucket_name
                ))
            raise ex
        except Exception as ex:
            logger.info('Could not retrieve the desired bucket due to'
                ' an unexpected error.'
            )
            raise ex
        try:
            return bucket.get_blob(object_name)
        except Exception as ex:
            return None

    def perform_interbucket_transfer(self, destination_blob, path):
        logger.info('Perform a bucket-to-bucket copy from {p} to {d}'.format(
            p=path,
            d = destination_blob
        ))
        source_blob = self.get_blob(path)
        if source_blob is not None:
            source_bucket = source_blob.bucket
            destination_bucket = destination_blob.bucket
            destination_object_name = destination_blob.name
            source_bucket.copy_blob(source_blob, \
                destination_bucket, \
                new_name=destination_object_name \
            )
            logger.info('Completed interbucket transfer.')
        else:
            logger.info('Source {p} was not found since the blob was None'.format(p=path))
            raise FileNotFoundError('Source file was not found at {p}'.format(p=path))
            
    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        logger.info('Store resource {pk} in Google bucket storage'.format(
            pk=resource_instance.pk)
        )

        relative_path = self.construct_relative_path(resource_instance)

        bucket = self.get_or_create_bucket()

        # this is the destination
        blob = storage.Blob(relative_path, bucket)

        # if the resource is on the server, we need to upload. If it's already in 
        # another bucket, just do a bucket transfer.

        final_path = os.path.join(self.BUCKET_PREFIX, self.BUCKET_NAME, relative_path)

        if os.path.exists(resource_instance.path): 
            try:
                self.upload_blob(blob, resource_instance.path)
            except Exception as ex:
                message = ('Failed to upload to bucket.  File will'
                    ' remain local on the server at path: {path}'.format(
                        path=resource_instance.path
                    )
                )
                raise Exception(message)
        else: # if it's not on our filesystem, assume it's in another bucket.
            # This assumes we are not "mixing" different cloud providers like AWS and GCP
            try:
                self.perform_interbucket_transfer(blob, resource_instance.path)
            except FileNotFoundError:
                logger.info('The source file ({path}) was not found and the interbucket'
                ' transfer failed.'.format(path = resource_instance.path))
                raise StorageException('Interbucket transfer failed, so file was not stored.')
            except Exception as ex:
                logger.error('Failed to transfer between buckets.  File will'
                    ' remain at: {path}'.format(
                        path=resource_instance.path
                    )
                )
                raise ex
        return final_path

    def delete(self, path):
        logger.info('Requesting deletion of file at {path}'.format(
            path=path
        ))
        if self.resource_exists(path):
            blob = self.get_blob(path)
        else:
            logger.error('Requested deletion of bucket-based file at {f}'
                ' which does not exist.'.format(f=path)
            )
            return
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

    def resource_exists(self, path):
        '''
        Returns true/false for whether the google-bucket based
        blob exists. Note that the google library is such that
        the blob will evaluate to None if it does not exist.
        '''
        try:
            blob = self.get_blob(path)
            if blob:
                return True
            return False
        except Exception:
            return False

    def localize_resource(self, resource_instance):
        '''
        Localizes the file and returns the path to the file
        on the local machine.
        
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
        relative_path = self.construct_relative_path(resource_instance)

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
            if blob is None:
                raise FileNotFoundError('The object located at {p} did not exist.'.format(
                        p = resource_instance.path
                    )
                )
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

    def get_download_url(self, resource_instance):
        '''
        Generate a signed URL for the object in google bucket storage.
        '''
        blob = self.get_blob(resource_instance.path)
        try:
            return blob.generate_signed_url(
                version = 'v4',
                expiration = datetime.timedelta(days=1),
                method='GET'
            )
        except Exception as ex:
            logger.error('Failed at generating the signed url for resource ({u})'.format(
                u = str(resource_instance.pk)
            ))  
            return None          

        