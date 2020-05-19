from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from api.models import Resource, Workspace
from api.resource_types import verify_resource_type

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
        # If we are using the serializer to validate internal calls, there
        # will not be a `requesting_user` key.
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
            d = ResourceSerializer.parse_request_parameters(validated_data)

            if d['workspace'] is None:
                return Resource.objects.create(
                    owner=resource_owner,
                    path=d['path'],
                    name=d['name'],
                    resource_type=d['resource_type'],
                    is_public=d['is_public'],
                    is_active=d['is_active'],
                    status=d['status']
                )
            else:
                # We need to check that the Workspace owner and the 
                # Resource owner are the same.
                workspace_owner = d['workspace'].owner
                if workspace_owner != resource_owner:
                    raise exceptions.ValidationError({
                        'workspace': 'Cannot assign a resource owned by {resource_owner}'
                        ' to a workspace owned by {workspace_owner}'.format(
                            workspace_owner = workspace_owner,
                            resource_owner = resource_owner
                        )
                    })

                return Resource.objects.create(
                    workspace=d['workspace'],
                    owner=resource_owner,
                    path=d['path'],
                    name=d['name'],
                    resource_type=d['resource_type'],
                    is_public=d['is_public'],
                    is_active=d['is_active'],
                    status=d['status']
                )     
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
        changing_resource_type = False
        new_resource_type = validated_data.get('resource_type', None)
        original_attributes = {}
        if new_resource_type:
            # if the type is different, reset the flag
            if new_resource_type != instance.resource_type:

                # store the original values of `is_public`, etc.
                # so that we can restore them once the validation is 
                # complete.
                original_attributes['is_active'] = instance.is_active
                original_attributes['is_public'] = instance.is_public
                changing_resource_type = True
                instance.status = 'Validating resource type change'
                instance.is_active = False
                instance.is_public = False
                instance.has_valid_resource_type = False

        # save the instance
        instance.save()

        # if the `resource_type` was changed in the request, start
        # the validation process.  Since it is calling an async, we
        # have to pass the primary key instead of the instance.
        if changing_resource_type:
            verify_resource_type(
                instance.pk, 
                new_resource_type, 
                original_attributes)

        return instance
        