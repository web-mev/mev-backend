from rest_framework import serializers

class FileFormatSerializer(serializers.Serializer):
    '''
    Serializer for describing the types of file formats
    available for resources
    '''
    key = serializers.CharField(max_length=10)
    description = serializers.CharField(max_length=2000)