import os

class BaseStorageBackend(object):
    
    def store(self, resource_instance):
        '''
        Handles moving the file described by the `resource_instance`
        arg to its final location.
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
        self.relative_path = os.path.join(owner_uuid, basename)