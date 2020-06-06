from django.core.cache import cache
from django.core.files.uploadhandler import FileUploadHandler

class UploadProgressCachedHandler(FileUploadHandler):
    '''
    Tracks progress for file uploads.
    The HTTP POST request must contain a header or query parameter, 'X-Progress-ID'
    which should contain a unique string to identify the upload to be tracked.
    Note that Django mutates 'X-Progress-ID' to 'HTTP_X_PROGRESS_ID'
    '''

    def __init__(self, request=None):
        super().__init__(request)
        self.progress_id = None
        self.cache_key = None

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        '''
        Override of the method from FileUploadHandler

            Parameters as copied from that parent class:

            input_data:
                An object that supports reading via .read().
            META:
                ``request.META``.
            content_length:
                The (integer) value of the Content-Length header from the
                client.
            boundary: The boundary from the Content-Type header. Be sure to
                prepend two '--'.

        '''
        self.content_length = content_length
        if 'HTTP_X_PROGRESS_ID' in self.request.GET :
            self.progress_id = self.request.GET['HTTP_X_PROGRESS_ID']
        elif 'HTTP_X_PROGRESS_ID' in self.request.META:
            self.progress_id = self.request.META['HTTP_X_PROGRESS_ID']
        if self.progress_id:
            self.cache_key = "%s_%s" % (self.request.META['REMOTE_ADDR'], self.progress_id )
            cache.set(self.cache_key, {
                'length': self.content_length,
                'uploaded' : 0
            })

    # This method needs to be here so that the other handlers can 
    # handle the creation of appropriate in-memory or temporary files
    def new_file(self, *args, **kwargs):
        pass

    def receive_data_chunk(self, raw_data, start):
        if self.cache_key:
            data = cache.get(self.cache_key)
            data['uploaded'] += self.chunk_size
            cache.set(self.cache_key, data)
        return raw_data

    # This method needs to be present, but the actual implementation
    # is left to the subsequent handler classes.
    def file_complete(self, file_size):
        pass

    def upload_complete(self):
        if self.cache_key:
            cache.delete(self.cache_key)
