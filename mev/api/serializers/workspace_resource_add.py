from rest_framework import serializers


class WorkspaceResourceAddSerializer(serializers.Serializer):
    '''
    When adding a Resource to a Workspace, we need to know
    the identifier for the original, unattached resource.
    '''
    resource_uuid = serializers.UUIDField(required=True)