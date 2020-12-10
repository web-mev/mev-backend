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
    is_ownerless = serializers.BooleanField(required=False, default=False)

    def validate_owner_email(self, email):
        if self.context['requesting_user'].email != email:
            raise serializers.ValidationError('Can only upload for your user')
        return email

    def validate(self, data):
        if 'is_ownerless' in data:
            if data['is_ownerless']:
                try:
                    owner_email = data['owner_email']
                    if len(owner_email) > 0:
                        raise serializers.ValidationError({'owner_email': 'Cannot'
                            ' simultaneously request an ownerless resource and provide'
                            ' an owner email'
                        })
                except KeyError:
                    pass
        return data


class DropboxUploadSerializer(serializers.Serializer):
    download_link = serializers.CharField(
        required=True
    )
    filename = serializers.CharField(
        required=True
    )