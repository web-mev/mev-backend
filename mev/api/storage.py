import uuid
import os

import boto3
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from api.utilities.basic_utils import copy_local_resource


class LocalResourceStorage(FileSystemStorage):

    def localize(self, resource, local_dir):
        '''
        Copies the file/resource from local filesystem storage into
        a local directory.

        This avoids conditionals when local processes (e.g. docker containers)
        need to use a file. We don't have to check whether we are using local
        or remote storage.
        '''
        name = str(uuid.uuid4())
        dest_path = os.path.join(local_dir, name)
        copy_local_resource(resource.datafile.path, dest_path)

    def copy_to_bucket(self, resource, dest_bucket_name, dest_object=None):
        raise NotImplementedError('Since local storage is used, we do not allow'\
            ' interaction with bucket/object storage.')


class S3ResourceStorage(S3Boto3Storage):
    bucket_name = settings.MEDIA_ROOT
    s3_prefix = 's3://'

    def localize(self, resource, local_dir):
        '''
        Downloads the file/resource from S3 storage into
        a local directory and returns the path on the local
        filesystem
        '''
        name = str(uuid.uuid4())
        dest_path = os.path.join(local_dir, name)
        s3 = boto3.client('s3')
        s3.download_file(settings.MEDIA_ROOT, resource.datafile.name, dest_path)
        return dest_path

    def _copy(self, src_bucket, dest_bucket, src_object, dest_object):
        '''
        A "private" method for general copies. Other public methods expose
        copies in and out of our storage. Use those methods instead.
        
        This performs a managed copy, which will perform multipart copy 
        if necessary (forfiles > 5Gb). 
        See https://boto3.amazonaws.com/v1/documentation/api/latest/reference\
            /services/s3.html#S3.Client.copy
        '''

        #TODO: catch bucket access issues
        s3 = boto3.resource('s3')
        copy_source = {
            'Bucket': src_bucket,
            'Key': src_object
        }
        s3.meta.client.copy(copy_source, dest_bucket, dest_object)
        return self.s3_prefix + os.path.join(
            dest_bucket,
            dest_object
        )

    def copy_to_storage(self, src_bucket, src_object, dest_object):
        '''
        Copies from a bucket outside of Django storage into our
        django-managed S3 storage

        `dest_object` is relative to our django-managed storage bucket
        '''
        return self._copy(
            src_bucket,
            self.bucket_name,
            src_object,
            dest_object
        )

    def copy_out_to_bucket(self, resource, dest_bucket_name, dest_object=None):
        '''
        Copies the resource to a destination at
        s3://<dest_bucket_name>/<dest_object>

        Since api.models.Resource objects can only reside in our
        storage bucket (see `bucket_name` above), this is a copy
        AWAY from our storage.

        If `dest_object` is None, we take the basename of the source `Resource`
        '''
        if dest_object is None:
            dest_object = str(uuid.uuid4())

        return self._copy(
            self.bucket_name,
            dest_bucket_name,
            resource.datafile.name,
            dest_object
        )