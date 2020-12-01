import os
import uuid
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.serializers.resource import ResourceSerializer
from api.models import Resource
from api.utilities.resource_utilities import set_resource_to_inactive
from api.async_tasks.async_resource_tasks import validate_resource_and_store

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

    def check_request_and_owner(self, payload, request):
        try:
            owner_email = payload['owner_email']
            if len(owner_email) == 0:
                owner = request.user
            else: # length of the owner_email field was non-zero
                try:
                    owner = User.objects.get(email=owner_email)
                except User.DoesNotExist:
                    raise ValidationError({'owner_email': 'Could not find owner'
                        ' with email: {owner}'.format(
                            owner=owner_email
                        )})
        except KeyError:
            owner = request.user
        return owner

    def handle_upload(self, request):
        self.owner = self.check_request_and_owner(request.data, request)

        # The resource type is NOT required, but may be specified.
        # If it's not explicitly set, we skip validation-- don't want
        # to guess at types.
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
            'is_public': self.is_public
        }
        rs = ResourceSerializer(data=d)

        # values were checked prior to this, but we enforce this again
        if rs.is_valid(raise_exception=True):
            r = rs.save()

            # set the size here since the ResourceSerializer has size
            # as a read-only field.  Hence, passing it to the ResourceSerializer
            # constructor above would ignore it.
            r.size = self.size
            r.save()
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


    def validate_and_store(self, resource_instance):
        '''
        Handles validation of Resources that are located locally 
        on the server.  Regardless of validation outcome, moves the
        uploaded Resource into its final storage.

        Note that we keep the validation and final storage operations 
        together so we don't spawn multiple async jobs which end up causing
        race conditions on updating the Resource instance's attributes. 
        '''

        # set and save attributes to prevent "use" of this Resource
        # before it is validated and in its final storage location:
        set_resource_to_inactive(resource_instance)

        # since the async method doesn't have a defined time to operate,
        # set a generic status on the Resource.
        resource_instance.status = Resource.PROCESSING
        resource_instance.save()

        # call the validation/storage methods async
        validate_resource_and_store.delay(
            resource_instance.pk, 
            self.resource_type 
        )


class RemoteUpload(BaseUpload):
    '''
    This is a base class for uploads that bypass the server
    and go directly to the storage backend.
    '''
    pass
