import os
import uuid
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from api.serializers.resource import ResourceSerializer
from api.models import Resource
from api.utilities.resource_utilities import set_resource_to_validation_status
import api.async_tasks as api_tasks

from resource_types import extension_is_consistent_with_type

User = get_user_model()

logger = logging.getLogger(__name__)

class BaseUpload(object):

    def __init__(self):

        # populate the other required members:
        self.filepath = None
        self.filename = None
        self.resource_type = None
        self.size = 0

    def handle_upload(self, request):
        try:
            owner_email = request.data['owner_email']
            try:
                owner = User.objects.get(email=owner_email)
            except User.DoesNotExist:
                return Response(
                    {'owner_email': 'Owner email not found.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except KeyError:
            owner = request.user

        self.owner = owner

        # The resource type is NOT required, but may be specified
        self.resource_type = request.data.get('resource_type')

        self.is_public = request.data.get('is_public', False)

    def create_resource_from_upload(self):

        # create a serialized representation so we can use the validation
        # contained there.  Note that since we are creating a new Resource
        # we have NOT validated it.  Hence, we explicitly set resource_type 
        # to be None
        d = {
            'owner_email': self.owner.email,
            'path': self.filepath,
            'name': self.filename,
            'resource_type': None,
            'is_public': self.is_public,
            'size': self.size
        }
        rs = ResourceSerializer(data=d)

        # values were checked prior to this, but we enforce this again
        if rs.is_valid(raise_exception=True):
            r = rs.save()
            return r


class LocalUpload(BaseUpload):
    '''
    This is a class for uploads that end up temporarily on the server
    (for validation or otherwise), before being sent to the storage backend
    '''

    @staticmethod
    def create_local_path(filename):

        tmp_name = '{uuid}.{filename}'.format(
            uuid = str(uuid.uuid4()),
            filename = filename
        )
        tmp_path = os.path.join(
            settings.PENDING_FILES_DIR, 
            tmp_name
        )
        return tmp_path


    def validate(self, resource_instance):
        '''
        Handles validation of Resources that are located locally 
        on the server.
        '''

        # if a resource_type was specified in the upload request,
        # we check that the type is consistent with the file suffix
        # and then validate if they are indeed consistent.
        if self.resource_type:
            logger.info('Resource type was {resource_type}'.format(
                resource_type=self.resource_type
            ))
            if extension_is_consistent_with_type(resource_instance.name, self.resource_type):
                # Now start the validation process (async):
                logger.info('Queueing validation for new resource %s with type %s ' % 
                    (str(resource_instance.pk), self.resource_type)
                )
                set_resource_to_validation_status(resource_instance)

                api_tasks.validate_resource.delay(
                    resource_instance.pk, 
                    self.resource_type 
                )
            else:
                logger.info('File extension was not consistent with the requested'
                    ' resource type.'
                )
                resource_instance.status = Resource.READY
                resource_instance.save()


class RemoteUpload(BaseUpload):
    '''
    This is a base class for uploads that bypass the server
    and go directly to the storage backend.
    '''
    pass
