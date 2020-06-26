import os

from django.core.exceptions import ImproperlyConfigured

from .base import BaseStorageBackend

try:
    GOOGLE_BUCKET_URL = os.environ['GOOGLE_BUCKET_URL']
except KeyError as ex:
    raise ImproperlyConfigured('Need to supply the following environment'
        ' variable: {k}'.format(k=ex))


class GoogleBucketStore(BaseStorageBackend):

    def create_bucket_if_not_exists(self):
        #TODO: implement
        pass

    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        super().store(resource_instance)

        final_url = os.path.join(GOOGLE_BUCKET_URL, self.relative_path)

        #TODO: complete implementation.

        resource_instance.path = final_url

    def delete(self, path):
        #TODO: implement
        pass

    def get_filesize(self, path):
        #TODO: implement
        pass