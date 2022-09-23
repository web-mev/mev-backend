import uuid
import os
from io import BytesIO
import logging

import boto3
import botocore
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from api.utilities.basic_utils import copy_local_resource
from api.utilities.resource_utilities import create_resource
from api.exceptions import StorageException

logger = logging.getLogger(__name__)


class LocalResourceStorage(FileSystemStorage):

    def get_absolute_path(self, path_relative_to_storage_root):
        return os.path.join(settings.MEDIA_ROOT, path_relative_to_storage_root)

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

    def copy_to_storage(self, src_bucket, src_object, dest_object):
        raise NotImplementedError('Since local storage is used, we do not allow'\
            ' interaction with bucket/object storage.')

    def create_resource_from_interbucket_copy(self, owner, src_path):
        raise NotImplementedError('Since local storage is used, we do not allow'\
            ' interaction with bucket/object storage.')

            
class S3ResourceStorage(S3Boto3Storage):
    bucket_name = settings.MEDIA_ROOT
    s3_prefix = 's3://'

    # This will append random chars to the end of the object name
    # so that files are not overwritten
    file_overwite = False

    def get_absolute_path(self, path_relative_to_storage_root):
        '''
        Returns the "full" s3:// 'path'.

        Used for situations like Cromwell, which is looking for a 
        full path to an object.

        `path_relative_to_storage_root` is typically from the `name`
        attribute of the FileField of the Resource class, e.g.
        r.datafile.name
        '''
        return f'{self.s3_prefix}{self.bucket_name}/{path_relative_to_storage_root}'

    def get_bucket_and_object_from_full_path(self, full_path):
        '''
        Given `full_path` (e.g. s3://my-bucket/folderA/file.txt)
        return a tuple of the bucket (`my-bucket`) and the object
        (`folderA/file.txt`)
        '''
        if not full_path.startswith(self.s3_prefix):
            raise Exception(f'The full path must \
                include the prefix {self.s3_prefix}')
        return full_path[len(self.s3_prefix):].split('/', 1)

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
        try:
            s3.meta.client.copy(copy_source, dest_bucket, dest_object)
        except botocore.exceptions.ClientError as ex:
            response_code = ex.response['Error']['Code']
            if response_code == '404':
                raise FileNotFoundError
        except Exception:
            raise StorageException('Unexpected error when performing a'
                ' bucket-to-bucket copy.'
            )
        return os.path.join(
            dest_bucket,
            dest_object
        )

    def copy_to_storage(self, src_bucket, src_object, dest_object=None):
        '''
        Copies from a bucket outside of Django storage into our
        django-managed S3 storage

        `dest_object` is relative to our django-managed storage bucket.
        If `dest_object` is None, we take the basename of the source object

        '''
        if dest_object is None:
            dest_object = os.path.basename(src_object)

        return self._copy(
            src_bucket,
            self.bucket_name,
            src_object,
            dest_object
        )

    def create_resource_from_interbucket_copy(self, owner, src_path):
        '''
        Copies an object into our storage and creates/returns
        a Resource instance.

        `src_path` is the FULL bucket path, e.g. s3://<BUCKET>/<object>
        '''
        src_bucket, src_object = self.get_bucket_and_object_from_full_path(src_path)

        # To avoid needing to duplicate the logic of locating files
        # within our storage, we basically create a dummy placeholder
        # "file" with empty content and create an instance
        # of api.models.Resource. We then get the path of that dummy
        # file and use that as a place to send the copy of our 
        # bucket-based file.
        with BytesIO() as fh:
            f = File(fh, str(uuid.uuid4()))
            r = create_resource(
                owner,
                file_handle=f,
                name=os.path.basename(src_object),
                # initially inactive so that a user can't interact with it (yet)
                is_active=False
            )
        dest_obj = r.datafile.name
        try:
            self.copy_to_storage(
                src_bucket,
                src_object,
                dest_obj
            )        
            # now that the file is copied to the correct location, update the 
            # api.models.Resource instance in the database.
            r.is_active = True
            r.save()
            return r
        except Exception as ex:
            logger.info('Caught an exception during in intrabucket copy.')
            # Need to delete that placeholder file and the database record
            self.delete(r.datafile.name)
            r.delete()
            raise ex

    def copy_out_to_bucket(self, resource, dest_bucket_name, dest_object=None):
        '''
        Copies the resource to a destination at
        s3://<dest_bucket_name>/<dest_object>

        Since api.models.Resource objects can only reside in our
        storage bucket (see `bucket_name` above), this is a copy
        AWAY from our storage.

        If `dest_object` is None, we create a new UUID-based name
        '''
        if dest_object is None:
            dest_object = str(uuid.uuid4())

        return self._copy(
            self.bucket_name,
            dest_bucket_name,
            resource.datafile.name,
            dest_object
        )