from uploaders.base import BaseUpload

class LocalUpload(BaseUpload):
    '''
    This is a class for uploads that end up temporarily on the server
    (for validation or otherwise), before being sent to the storage backend
    '''
    def validate(self):
        pass