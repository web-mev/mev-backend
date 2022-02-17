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
                    if owner != request.user:
                        raise ValidationError({'owner_email': 'Could not find that '
                            'owner or assign a file to anyone but yourself.'
                        })
                except User.DoesNotExist:
                    raise ValidationError({'owner_email': 'Could not find owner'
                        ' with email: {owner}'.format(
                            owner=owner_email
                        )})
        except KeyError:
            owner = request.user
        return owner

    def handle_upload(self, request, serialized_data):
        self.owner = self.check_request_and_owner(request.data, request)

        # check if it was requested that this uploaded resource be ownerless
        try:
            is_ownerless = request.data['is_ownerless']
            if is_ownerless:
                if request.user.is_staff:
                    self.owner = None
                else: # regular users can't request ownerless
                    raise ValidationError({'is_ownerless': 'Non-admins cannot request'
                        ' that a resource be without an owner'
                    })
        except KeyError:
            is_ownerless = False

        # check the public status from the request:
        is_public = serialized_data.get('is_public', False)
        if is_public and (self.owner is not None):
            raise ValidationError({'is_public': 'Cannot request a resource'
                ' be public if it has an owner.'
            })
        self.is_public = is_public

        # The resource type is NOT required, but may be specified.
        # If it's not explicitly set, we skip validation-- don't want
        # to guess at types.
        self.resource_type = serialized_data.get('resource_type')

    def create_resource_from_upload(self):

        # create a serialized representation so we can use the validation
        # contained there.  Note that since we are creating a new Resource
        # we have NOT validated it.  Hence, we explicitly set resource_type 
        # to be None
        if self.owner:
            owner_email = self.owner.email
        else:
            owner_email = None
        d = {
            'owner_email': owner_email,
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
    def create_local_path(extension):

        if extension is not None:
            tmp_name = '{uuid}.{extension}'.format(
                uuid = str(uuid.uuid4()),
                extension = extension
            )
        else: 
            tmp_name = str(uuid.uuid4())
            
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
    # the name of the folder inside the bucket where the files will be sent
    # Note that it's not the final storage location, but rather a temporary
    # location
    tmp_folder_name = 'uploads-tmp'