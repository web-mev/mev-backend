import uuid
import logging 

from rest_framework.exceptions import APIException, ValidationError
from .base import LocalUpload
from api.utilities import normalize_filename
from api.exceptions import StringIdentifierException

logger = logging.getLogger(__name__)

class ServerLocalUpload(LocalUpload):
    '''
    This uploader class handles uploads to the server directly
    from a user's machine.  The file data is sent as raw bytes
    and we have to parse it out of the request payload.
    '''
    def handle_upload(self, request, serialized_data):
        super().handle_upload(request, serialized_data)

        # get the remainder of the payload parameters
        upload = request.data['upload_file']

        # preserve the user-supplied file name (e.g. the basename)
        self.filename = upload.name
        logger.info('Upload filename: {f}'.format(f=self.filename))

        # generate a resource UUID which we can use to name the file. This
        # UUID will also be used as the primary key in the db.
        self.upload_resource_uuid = uuid.uuid4()
        logger.info('Upload resource UUID={x}'.format(x=str(self.upload_resource_uuid)))

        tmp_path = LocalUpload.create_local_path(self.upload_resource_uuid)
        logger.info('Temporary file upload will be placed at {t}'.format(
            t = tmp_path
        ))

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

        return self.create_resource_from_upload()
        
