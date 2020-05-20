from rest_framework import serializers

from api.resource_types import DATABASE_RESOURCE_TYPES

class UploadSerializer(serializers.Serializer):
    owner_email = serializers.EmailField(required=False)
    resource_type = serializers.ChoiceField(
        choices=DATABASE_RESOURCE_TYPES
    )
    upload_file = serializers.FileField()