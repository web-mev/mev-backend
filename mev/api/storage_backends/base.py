import os
import logging

from api.models import Resource, OperationResource

logger = logging.getLogger(__name__)


class BaseStorageBackend(object):
    
    @staticmethod
    def construct_relative_path(resource_instance):
        '''
        Creates a path relative to the storage "root". Depending on whether
        the Resource is user-associated or user-independent, we have different
        relative paths.
        '''

        # create a final file location by concatenating the
        # resource UUID and the file's "human readable" name
        basename = '{uuid}.{name}'.format(
            uuid=resource_instance.pk, 
            name=resource_instance.name
        )

        if type(resource_instance) == Resource:

            if resource_instance.owner:
                # since we will organize files by user ID, get their unique ID
                owner_uuid = str(resource_instance.owner.user_uuid)

                # make the path relative to the storage "root"
                return os.path.join(
                    Resource.USER_RESOURCE_STORAGE_DIRNAME, 
                    owner_uuid, 
                    basename)

            else:
                return os.path.join(Resource.OTHER_RESOURCE_STORAGE_DIRNAME,basename)

        elif type(resource_instance) == OperationResource:
            return os.path.join(
                OperationResource.OPERATION_RESOURCE_DIRNAME,
                str(resource_instance.operation.id),
                basename
            )
        else:
            logger.error('Unexpected type passed. Should be a Resource or child thereof.')
            raise Exception('Unexpected type used when attempting to construct'
                ' a relative path for the storage backend.'
            )

    def resource_exists(self, path):
        raise NotImplementedError('Must implement this method in a child class.')