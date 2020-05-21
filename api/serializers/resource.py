from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from api.resource_types import DATABASE_RESOURCE_TYPES
from api.models import Resource, Workspace
from api.utilities.resource_utilities import set_resource_to_validation_status
import api.async_tasks as api_tasks

class ResourceSerializer(serializers.ModelSerializer):

    # add a human-readable datetime
    created = serializers.DateTimeField(
        source='creation_datetime', 
        format = '%B %d, %Y (%H:%M:%S)',
        read_only=True
    )
    owner_email = serializers.EmailField(source='owner.email', required=False)
    workspace = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(),
        required=False
    )
    path = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Resource
        fields = [
            'id',
            'url',
            'name',
            'resource_type',
            'owner_email',
            'is_active',
            'is_public',
            'status',
            'workspace',
            'created',
            'path'
        ]

    @staticmethod
    def parse_request_parameters(validated_data):
        '''
        This is a helper function to parse out the various 
        optional parameters from the request to create or
        edit a Resource
        '''
        path = validated_data.get('path', '')
        name = validated_data.get('name', '')
        workspace = validated_data.get('workspace', None),
        resource_type = validated_data.get('resource_type', None)
        is_public = validated_data.get('is_public', False)
        is_active = validated_data.get('is_active', False)
        status = validated_data.get('status', '')

        # the 'get' above returns a tuple so we have to index
        # to get the actual workspace instance or None
        workspace = workspace[0]

        return {
            'path': path,
            'name': name,
            'workspace': workspace, 
            'resource_type': resource_type,
            'is_public' : is_public,
            'is_active' : is_active,
            'status': status
        }

    def create(self, validated_data): 

        # the user who generated the request.  A User instance (or subclass)
        # who MUST be an admin.  Regular users cannot create `Resources`
        # via API calls.
        # If we are using the serializer to validate data when creating
        # Resources internally, there will not be a `requesting_user` key.

        internal_call = False
        try:
            requesting_user = validated_data['requesting_user']
        except KeyError:
            internal_call = True

        owner_email = validated_data['owner']['email']

        # check that the owner does exist
        try:
            resource_owner = get_user_model().objects.get(email=owner_email)
        except get_user_model().DoesNotExist as ex:
            raise exceptions.ParseError()

        # If the user is an admin, they can create a Resource for anyone.
        # The DRF permissions should catch problems before here, but this is
        # extra insurance
        if internal_call or requesting_user.is_staff:
            params = ResourceSerializer.parse_request_parameters(validated_data)
            
            # we require the resource_type
            resource_type = params['resource_type']
            if not resource_type:
                raise exceptions.ValidationError({
                    'resource_type': 'This field is required and cannot be null.'
                })

            if params['workspace'] is None:
                resource = Resource.objects.create(
                    owner=resource_owner,
                    path=params['path'],
                    name=params['name'],
                    is_public=params['is_public']
                )
            else:
                # We need to check that the Workspace owner and the 
                # Resource owner are the same.
                workspace_owner = params['workspace'].owner
                if workspace_owner != resource_owner:
                    raise exceptions.ValidationError({
                        'workspace': 'Cannot assign a resource owned by {resource_owner}'
                        ' to a workspace owned by {workspace_owner}'.format(
                            workspace_owner = workspace_owner,
                            resource_owner = resource_owner
                        )
                    })

                resource = Resource.objects.create(
                    workspace=params['workspace'],
                    owner=resource_owner,
                    path=params['path'],
                    name=params['name'],
                    is_public=params['is_public']
                )

            set_resource_to_validation_status(resource)
            api_tasks.validate_resource.delay(
                resource.pk, 
                resource_type 
            )
            return resource
        else:
            raise exceptions.PermissionDenied()

    def update(self, instance, validated_data):
        '''
        When a user updates a Resource, they can only do a few things--
        - remove from a `Workspace` (since adding to a `Workspace` is an
        implicit copy).  This will DELETE the workspace-associated
        `Resource` since the original is still there.
        - change the name
        - change the resource type (which triggers a type validation)
        - change public or private

        In addition to these, admins may also change:
        - is_active
        - status
        - path
        '''
        # if we are performing validation, or some other action has 
        # set the resource "inactive", we cannot make changes 
        if not instance.is_active:
            raise exceptions.ParseError('The requested Resource'
            ' is not currently activated, possibly due to pending'
            ' validation.  Please wait and try again.')

        requesting_user = validated_data['requesting_user']

        # we could just ignore any data attempting to
        # change the owner of the Resource, but
        # we will explicitly reject any attempts.
        original_owner_email = instance.owner.email
        new_requested_owner = validated_data.get('owner', None)
        if new_requested_owner:
            new_owner_email = new_requested_owner['email']
            if original_owner_email != new_owner_email:
                raise exceptions.ParseError('Cannot change the owner of a workspace.')

        # Note that we cannot change the workspace with this method.
        # Providing a workspace is not an error provided the workspace (if assigned)
        # happens to be the same.
        # we could ignore requests to change the associated workspace, but it is
        # more helpful to issue a message.
        if validated_data.get('workspace', None):
            if validated_data['workspace'] != instance.workspace:
                raise exceptions.ParseError('Cannot change the workspace directly.'
                    ' Remove it from the workspace (if possible) and then add it'
                    ' to the desired workspace'
                )

        # the following are fields able to be edited by regular users and admins:
        instance.name = validated_data.get('name', instance.name)
        instance.is_public = validated_data.get('is_public', instance.is_public)

        # fields that can only be edited by admins:
        if requesting_user.is_staff:
            instance.is_active = validated_data.get('is_active', instance.is_active)
            instance.status = validated_data.get('status', instance.status)
            instance.path = validated_data.get('path', instance.path)

        # if the resource_type was sent in the request, we will eventually
        # kick off an async process for validating the type.  Until that 
        # happens, however, we simply change the status and save.  Note that  
        # the resource_type has NOT changed yet.  
        # 
        # If the validation succeeds, then the `resource_type` and
        # that status will be changed.
        #
        # Also note that we change the status immediately since the async
        # task might lag and not be executed immediately.

        changing_resource_type = False
        new_resource_type = validated_data.get('resource_type', None)
        if new_resource_type:
            # if the type is different, reset the flag
            if new_resource_type != instance.resource_type:
                changing_resource_type = True
                set_resource_to_validation_status(instance)

        # save the instance
        instance.save()

        # if the `resource_type` was changed in the request, start
        # the validation process.  Since it is calling an async, we
        # have to pass the primary key instead of the instance.
        if changing_resource_type:
            api_tasks.validate_resource.delay(
                instance.pk, 
                new_resource_type
            )

        return instance
        