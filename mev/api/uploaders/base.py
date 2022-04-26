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


from resource_types import extension_is_consistent_with_type

User = get_user_model()

logger = logging.getLogger(__name__)

class BaseUpload(object):

    def __init__(self):

        # populate the other required members:
        self.filepath = None
        self.filename = None
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

    def create_resource_from_upload(self):

        # create a serialized representation so we can use the validation
        # contained there.  Note that since we are creating a new Resource
        # we have NOT validated it.  Hence, we explicitly set resource_type 
        # to be None. 
        if self.owner:
            owner_email = self.owner.email
        else:
            owner_email = None
        d = {
            'id': str(self.upload_resource_uuid),
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
    def create_local_path(upload_resource_uuid):
        tmp_name = str(upload_resource_uuid)
        tmp_path = os.path.join(
            settings.PENDING_FILES_DIR, 
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