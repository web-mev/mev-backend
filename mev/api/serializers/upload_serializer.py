from rest_framework import serializers


class DropboxUploadSerializer(serializers.Serializer):
    download_link = serializers.CharField(
        required=True
    )
    filename = serializers.CharField(
        required=True
    )
