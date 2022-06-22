import os
import uuid
import logging

from django.conf import settings

from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.utilities.admin_utils import alert_admins
from api.serializers.resource import ResourceSerializer
from api.models import Resource


logger = logging.getLogger(__name__)

class BaseUpload(object):

    def __init__(self):

        # populate the other required members:
        self.filepath = None
        self.filename = None
        self.size = 0

    def check_request_and_owner(self, payload, request):
        '''
        This function provides an opportunity to implement custom checks
        related to ownership of a file/resource.
        '''
        return request.user

    def handle_upload(self, request, serialized_data):
        '''
        `handle_upload` is the main entry method for the uploader classes. 
        Implement specialized behavior in children class methods.
        '''
        self.owner = self.check_request_and_owner(request.data, request)
        self.is_public = False

    def create_resource_from_upload(self):

        # create a serialized representation of the Resource we are creating
        # so we can use the validation contained in the ResourceSerializer.

        # Note that since we are creating a new Resource
        # we have NOT validated it.  Hence, we explicitly set resource_type 
        # to be None. Similar for the file_format
        
        d = {
            'id': str(self.upload_resource_uuid),
            'owner_email': self.owner.email,
            'path': self.filepath,
            'name': self.filename,
            'resource_type': None,
            'file_format': None,
            'is_public': self.is_public
        }
        rs = ResourceSerializer(data=d)

        # values were checked prior to this, but we enforce this again
        if rs.is_valid():
            r = rs.save()
            # set the size here since the ResourceSerializer has size
            # as a read-only field.  Hence, passing it to the ResourceSerializer
            # constructor above would ignore it.
            r.size = self.size
            r.save()
            return r
        else:
            message = 'Encountered an invalid Resource serializer when creating' \
                ' a new Resource instance during upload.'
            logger.info(message)
            alert_admins(message)
            return




class LocalUpload(BaseUpload):
    '''
    This is a class for uploads that end up temporarily on the server
    (for validation or otherwise), before being sent to the storage backend
    '''

    @staticmethod
    def create_local_path(upload_resource_uuid):
        tmp_name = str(upload_resource_uuid)
        tmp_path = os.path.join(
            settings.PENDING_UPLOADS_DIR, 
            tmp_name
        )
        return tmp_path


class RemoteUpload(BaseUpload):
    '''
    This is a base class for uploads that bypass the server
    and go directly to the storage backend.
    '''
    # the name of the folder inside the bucket where the files will be sent
    # Note that it's not the final storage location, but rather a temporary
    # location
    tmp_folder_name = 'uploads-tmp'