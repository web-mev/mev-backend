from django.contrib.auth import get_user_model
from rest_framework import serializers, exceptions

from api.models import Workspace

class WorkspaceSerializer(serializers.ModelSerializer):

    # add a human-readable datetime
    readable_datetime = serializers.CharField(source='get_readable_datetime', read_only=True)
    owner_email = serializers.EmailField(source='owner.email')

    class Meta:
        model = Workspace
        fields = [
            'url',
            'id',
            'workspace_name',
            'creation_datetime',
            'owner_email',
            'readable_datetime'
        ]
        read_only_fields = ['creation_datetime', 'readable_datetime']

    def create(self, validated_data): 

        # the user who generated the request.  A User instance (or subclass)
        requesting_user = validated_data['requesting_user']
        owner_email = validated_data['owner']['email']

        try:
            workspace_owner = get_user_model().objects.get(email=owner_email)
        except get_user_model().DoesNotExist as ex:
            raise exceptions.ParseError()

        # If the user is an admin, they can create a Workspace for anyone.
        # if the user is not an admin, they can only create Workspaces for themself.
        if requesting_user.is_staff or (workspace_owner == requesting_user):
            return Workspace.objects.create(owner=workspace_owner)
        else:
            raise exceptions.PermissionDenied()


    def update(self, instance, validated_data):

        # we could just ignore any data attempting to
        # change the owner of the Workspace, but
        # we will explicitly reject any attempts.
        original_owner_email = instance.owner.email
        new_requested_owner = validated_data.get('owner', None)
        if new_requested_owner:
            new_owner_email = new_requested_owner['email']
            if original_owner_email != new_owner_email:
                raise exceptions.ParseError('Cannot change the owner of a workspace.')

        instance.workspace_name = validated_data.get('workspace_name', instance.workspace_name)
        instance.save()
        return instance
        