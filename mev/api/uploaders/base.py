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