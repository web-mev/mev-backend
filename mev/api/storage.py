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


class S3ResourceStorage(S3Boto3Storage):
    bucket_name = settings.MEDIA_ROOT

    def localize(self, resource, local_dir):
        '''
        Downloads the file/resource from S3 storage into
        a local directory
        '''
        name = str(uuid.uuid4())
        dest_path = os.path.join(local_dir, name)
        s3 = boto3.client('s3')
        s3.download_file(settings.MEDIA_ROOT, resource.datafile.name, dest_path)
        return dest_path