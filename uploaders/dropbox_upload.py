from uploaders.base import LocalUpload, RemoteUpload


class DropboxLocalUpload(LocalUpload):
    '''
    This handles Dropbox-specific behavior for files that are initially uploaded
    to the MEV server before going to the final storage backend
    '''
    pass


class DropboxRemoteUpload(RemoteUpload):
    '''
    This handles Dropbox-specific behavior for files that go directly to the 
    storage backend.
    '''
    pass