from rest_framework import serializers

from api.data_structures import OperationOutput
from api.serializers.output_spec import OutputSpecSerializer

class OperationOutputSerializer(serializers.Serializer):

    output_spec = OutputSpecSerializer(required=True)

    def create(self, validated_data):
        '''
        Returns an OperationOutput instance from the validated
        data.
        '''
        return OperationOutput(validated_data['spec'])

    def get_instance(self):
        '''
        A more suggestive way to retrieve the OperationOutput
        instance from the serializer than `save()`, since
        we are not actually saving OperationOutput instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)