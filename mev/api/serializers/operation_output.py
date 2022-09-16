from rest_framework import serializers

from api.data_structures import OperationOutput
from api.serializers.output_spec import OutputSpecSerializer

class OperationOutputSerializer(serializers.Serializer):

    required = serializers.BooleanField(required=True)
    spec = OutputSpecSerializer(required=True)
    converter = serializers.CharField(max_length=500, required=True)

    def to_representation(self, instance):
        if type(instance) == OperationOutput:
            return instance.to_dict()
        else:
            return instance

    def create(self, validated_data):
        '''
        Returns an OperationOutput instance from the validated
        data.
        '''
        spec = OutputSpecSerializer(data=validated_data['spec']).get_instance()
        return OperationOutput(
            spec, 
            validated_data['converter'], 
            validated_data['required']
        )

    def get_instance(self):
        '''
        A more suggestive way to retrieve the OperationOutput
        instance from the serializer than `save()`, since
        we are not actually saving OperationOutput instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)