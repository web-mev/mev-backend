from rest_framework import serializers


class UploadSerializer(serializers.Serializer):
    upload_file = serializers.FileField()


class DropboxUploadSerializer(serializers.Serializer):
    download_link = serializers.CharField(
        required=True
    )
    filename = serializers.CharField(
        required=True
    )