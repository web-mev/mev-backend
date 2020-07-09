import os

class BaseStorageBackend(object):
    
    @staticmethod
    def construct_relative_path(resource_instance):
        '''
        Creates a path relative to the storage "root"
        '''

        # since we will organize files by user ID, get their unique ID
        owner_uuid = str(resource_instance.owner.user_uuid)

        # create a final file location by concatenating the
        # resource UUID and the file's "human readable" name
        basename = '{uuid}.{name}'.format(
            uuid=resource_instance.pk, 
            name=resource_instance.name
        )

        # make the path relative to the storage "root"
        return os.path.join(owner_uuid, basename)