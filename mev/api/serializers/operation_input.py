from rest_framework import serializers

from api.data_structures import OperationInput
from api.serializers.input_spec import InputSpecSerializer

class OperationInputSerializer(serializers.Serializer):

    description = serializers.CharField(max_length=5000, required=True)
    name = serializers.CharField(max_length=100, required=True)
    required = serializers.BooleanField(required=True)
    spec = InputSpecSerializer(required=True)

    def to_representation(self, instance):
        if type(instance) == OperationInput:
            return instance.to_dict()
        else:
            instance['spec'] = instance['spec'].to_dict()           
            return instance

    def create(self, validated_data):
        '''
        Returns an OperationInput instance from the validated
        data.
        '''
        return OperationInput(validated_data['description'], 
            validated_data['name'], 
            validated_data['spec'], 
            validated_data['required']
        )

    def get_instance(self):
        '''
        A more suggestive way to retrieve the OperationInput
        instance from the serializer than `save()`, since
        we are not actually saving OperationInput instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)