import os
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from api.utilities.basic_utils import make_local_directory, \
    move_resource, \
    delete_local_file
from .base import BaseStorageBackend

try:
    USER_STORAGE_DIRNAME = os.environ['LOCAL_USER_STORAGE_DIRNAME']
except KeyError as ex:
    raise ImproperlyConfigured('Need to supply the following environment'
        ' variable: {k}'.format(k=ex))

logger = logging.getLogger(__name__)

class LocalStorage(BaseStorageBackend):

    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
        '''
        print('in local.store')
        super().store(resource_instance)

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

    def delete(self, path):
        delete_local_file(path)

    def get_filesize(self, path):
        try:
            return os.path.getsize(path)
        except FileNotFoundError:
            logger.error('Failed to get the size of local file at {path}'
            ' since it did not exist.'.format(path=path))
        except Exception as ex:
            logger.error('Caught some unexpected exception when calling'
            ' os.path.getsize.  Exception was {ex}'.format(ex=ex))
        # since file-size is not "critical", we log the errors and just
        # return 0 since it will still work.
        return 0