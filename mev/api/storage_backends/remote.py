from .base import BaseStorageBackend

class RemoteStorageBackend(BaseStorageBackend):
    '''
    Base class for all storage systems that are not local to the server.

    Typically, a concrete implementation of a storage interface will
    be created as a child class.
    '''

    def __init__(self):
        super().__init__()