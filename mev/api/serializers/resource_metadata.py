from rest_framework import serializers, exceptions

from api.models import ResourceMetadata, \
    Resource, \
    ExecutedOperation

class ResourceMetadataSerializer(serializers.ModelSerializer):

    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all()
    )

    class Meta:
        model = ResourceMetadata
        fields = [
            'resource',
            'parent_operation',
            'observation_set',
            'feature_set'
        ]