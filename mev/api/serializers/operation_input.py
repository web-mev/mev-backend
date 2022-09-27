from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from data_structures.operation_input import OperationInput
from api.serializers.input_spec import InputSpecSerializer

class OperationInputSerializer(serializers.Serializer):

    description = serializers.CharField(max_length=5000, required=True)
    name = serializers.CharField(max_length=100, required=True)
    required = serializers.BooleanField(required=True)
    spec = InputSpecSerializer(required=True)
    converter = serializers.CharField(max_length=500, required=True)

    def to_representation(self, instance):
        if type(instance) == OperationInput:
            return instance.to_dict()
        else:
            return instance

    def create(self, validated_data):
        '''
        Returns an OperationInput instance from the validated
        data.
        '''
        spec = InputSpecSerializer(data=validated_data['spec']).get_instance()
        return OperationInput(validated_data['description'], 
            validated_data['name'], 
            spec, 
            validated_data['converter'],
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

    def is_valid(self, raise_exception=False):
        if hasattr(self, 'initial_data'):
            payload_keys = set(self.initial_data.keys()) # all the payload keys
            serializer_fields = set(self.fields.keys()) # all the serializer fields
            extra_fields = payload_keys.difference(serializer_fields)
            #filter(lambda key: key not in serializer_fields , payload_keys) 
            if len(extra_fields) > 0:
                raise ValidationError('Extra fields ({s}) in payload'.format(
                    s=','.join(extra_fields))
                )
        return super().is_valid(raise_exception)