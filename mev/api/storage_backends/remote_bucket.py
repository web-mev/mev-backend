import os

from django.core.exceptions import ImproperlyConfigured

from .remote import RemoteStorageBackend

class RemoteBucketStorageBackend(RemoteStorageBackend):
    '''
    A specialization of remote storage that is based on
    bucket/object storage, such as S3 or GCP bucket.
    '''
    def __init__(self):
        try:
            self.BUCKET_NAME = os.environ['USER_STORAGE_BUCKET_NAME']
        except KeyError as ex:
            raise ImproperlyConfigured('For bucket-based storage, you'
                ' need to supply the following environment'
                ' variable: {k}'.format(k=ex)
            )
        super().__init__()