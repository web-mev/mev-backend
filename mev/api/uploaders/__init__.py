from django.conf import settings

from .dropbox_upload import DROPBOX, \
    DropboxLocalUpload, \
    DropboxGCPRemoteUpload, \
    DropboxAWSRemoteUpload

uploader_list = [
    DropboxLocalUpload,
    DropboxGCPRemoteUpload,
    DropboxAWSRemoteUpload
]

def get_async_uploader(uploader_id):
    '''
    A single function which handles the logic of which async uploader to use.

    Returns an instantiated uploader
    '''
    if uploader_id == DROPBOX:
        # if local storage, we don't need to worry about which cloud
        # provider
        if settings.STORAGE_LOCATION == settings.LOCAL:
            return DropboxLocalUpload()
        elif settings.STORAGE_LOCATION == settings.REMOTE:
            # If we are using remote storage, then we have to know
            # which cloud environment so we can use the proper uploader
            if settings.CLOUD_PLATFORM == settings.GOOGLE:
                return DropboxGCPRemoteUpload()            
            elif settings.CLOUD_PLATFORM == settings.AMAZON:
                return DropboxAWSRemoteUpload()