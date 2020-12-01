from .local_upload import ServerLocalUpload
from .dropbox_upload import DropboxLocalUpload, DropboxRemoteUpload

# to provide a common interface for uploading, we have an asynchronous
# function that takes a class name (the __name__ member of a class)
# To allow that async function to instantiate the proper class, we provide a
# lookup function below. Thus, the only classes in the list below should be
# those which expose the `async_upload` method
uploader_list = [ServerLocalUpload, DropboxRemoteUpload, DropboxLocalUpload]
uploader_mapping = {x.__name__ for x in uploader_list}

def get_uploader_by_name(name):
    try:
        return uploader_mapping[name]
    except KeyError as ex:
        raise Exception('The uploader with name "{n}" has not been'
            ' registered through this function, or does not exist. Names'
            ' are: {names}'.format(names=', '.join(uploader_mapping.keys()))
        )