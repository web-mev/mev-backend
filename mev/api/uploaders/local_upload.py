import logging
from rest_framework.exceptions import APIException

from .base import LocalUpload

logger = logging.getLogger(__name__)

class ServerLocalUpload(LocalUpload):
    '''
    This uploader class handles uploads to the server directly
    from a user's machine.  The file data is sent as raw bytes
    and we have to parse it out of the request payload.
    '''
    def handle_upload(self, request):
        super().handle_upload(request)

        # get the remainder of the payload parameters
        upload = request.data['upload_file']

        # grab the file name from the upload request
        self.filename = upload.name
        tmp_path = LocalUpload.create_local_path(self.filename)

        self.size = upload.size

        # and write to a temporary directory where
        # we stage files pre-validation
        try:
            with open(tmp_path, 'wb+') as destination:
                for chunk in upload.chunks():
                    destination.write(chunk)
            # this sets a temporary local path which will be assigned
            # to the Resource's path.  Eventually that member will be updated
            # after the file is validated and sent to its final storage
            self.filepath = tmp_path
        except Exception as ex:
            logger.error('An exception was raised when writing a local upload to the tmp directory.')
            logger.error(ex)
            raise APIException('The upload process experienced an error.')

        # create a Resource instance.
        # Note that this also performs validation
        # and temporarily disables the Resource via the `is_active` flag
        return self.create_resource_from_upload()
        
