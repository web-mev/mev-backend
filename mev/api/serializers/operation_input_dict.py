from rest_framework import serializers

from data_structures.operation_input import OperationInput
from data_structures.operation_input_output_dict import OperationInputDict
from api.serializers.operation_input import OperationInputSerializer

class OperationInputDictSerializer(serializers.BaseSerializer):
    '''
    Inside each `Operation` instance is a dictionary addressed by `inputs`.

    Each item in that dict is an instance of OperationInput
    (and the keys are simple strings)
    '''

    def to_representation(self, instance):
        return instance.to_dict()

    def to_internal_value(self, data):
        internal_val = {}
        if type(data) != dict:
            raise serializers.ValidationError('Inputs must be '
                ' formatted as a mapping/dict.  For example, {"some name":'
                ' <OperationInput>}')  
        for k in data.keys():
            v = data[k]
            if type(v) == dict:
                # turn the dict giving an `OperationInput` into an actual
                # instance of `OperationInput`
                v = OperationInputSerializer(data=v)
                v = v.get_instance()
            internal_val[k]=v
        return internal_val

    def create(self, validated_data):
        d = {}
        for k in validated_data.keys():
            item = validated_data[k]
            if type(item) == OperationInput:
                d[k] = item
            elif type(item) == dict:
                os = OperationInputSerializer(data=item)
                d[k] = os.get_instance()
        return OperationInputDict(d)

    def get_instance(self):
        '''
        The `save` method of serializers could work here, but this 
        naming is more suggestive since we are not actually saving attributes
        to any database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)