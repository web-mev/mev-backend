from wsgiref import validate
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework import serializers
from api.models.simple_resource import SimpleResource

class SimpleResourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = SimpleResource
        fields = ['path', 'owner']
        #read_only_fields = ['owner']

    def create(self, validated_data):
        print(validated_data)
        x= super().create(validated_data)
        x.name = x.path.name
        x.save()
        return x

class SimpleUploadView(CreateAPIView):
    parser_classes = [MultiPartParser]
    serializer_class = SimpleResourceSerializer

    def perform_create(self, serializer):
       serializer.save(owner=self.request.user)