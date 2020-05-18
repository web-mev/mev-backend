from rest_framework import serializers

class UploadSerializer(serializers.Serializer):
    owner = serializers.EmailField(required=False)
    resource_type = serializers.CharField(max_length=50)
    upload_file = serializers.FileField()