from .base import BaseStorageBackend

class RemoteStorageBackend(BaseStorageBackend):
    '''
    Base class for all storage systems that are not local to the server.

    Typically, a concrete implementation of a storage interface will
    be created as a child class.
    '''

    is_local_storage = False

    def __init__(self):
        super().__init__()

    def get_download_url(self, resource_instance):
        raise NotImplementedError('Override this method in a child class.')