import logging

from rest_framework import serializers, exceptions

from api.serializers.file_format import FileFormatSerializer

logger = logging.getLogger(__name__)

class ResourceTypeSerializer(serializers.Serializer):
    '''
    Serializer for describing the types of available Resources
    that users may choose.
    '''
    resource_type_key = serializers.CharField(max_length=50)
    resource_type_title = serializers.CharField(max_length=250)
    resource_type_description = serializers.CharField(max_length=2000)
    acceptable_formats = FileFormatSerializer(many=True, read_only=True)
    example = serializers.JSONField()