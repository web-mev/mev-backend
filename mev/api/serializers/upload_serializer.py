from rest_framework import serializers

from resource_types import DATABASE_RESOURCE_TYPES

class UploadSerializer(serializers.Serializer):
    owner_email = serializers.EmailField(required=False)
    resource_type = serializers.ChoiceField(
        choices=DATABASE_RESOURCE_TYPES,
        required = False
    )
    upload_file = serializers.FileField()
    is_public = serializers.BooleanField(required=False)

    def validate_owner_email(self, email):
        if self.context['requesting_user'].email != email:
            raise serializers.ValidationError('Can only upload for your user')
        return email