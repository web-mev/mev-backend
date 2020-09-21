from rest_framework import serializers

from api.data_structures import OperationOutput
from api.serializers.operation_output import OperationOutputSerializer

class OperationOutputDictSerializer(serializers.BaseSerializer):
    '''
    Inside each `Operation` instance is a dictionary addressed by `outputs`.

    Each item in that dict is an instance of OperationOutput
    (and the keys are simple strings)
    '''

    def to_representation(self, instance):
        output = {}
        for key, op_output in instance.items():
            output[key] = OperationOutputSerializer(op_output).data
        return output

    def to_internal_value(self, data):
        internal_value = {}
        if type(data) != dict:
            raise serializers.ValidationError('Outputs must be '
                ' formatted as a mapping/dict.  For example, {"some name":'
                ' <OperationOutput>}')  
        for k in data.keys():
            v = data[k]
            if type(v) == dict:
                # turn the dict giving an `OperationOutput` into an actual
                # instance of `OperationOutput`
                v = OperationOutputSerializer(data=v)
                v = v.get_instance()
            internal_value[k]=v
        return internal_value

    def create(self, validated_data):
        d = {}
        for k in validated_data.keys():
            item = validated_data[k]
            if type(item) == OperationOutput:
                d[k] = item
            elif type(item) == dict:
                os = OperationOutputSerializer(data=item)
                d[k] = os.get_instance()
        return d

    def get_instance(self):
        '''
        The `save` method of serializers could work here, but this 
        naming is more suggestive since we are not actually saving attributes
        to any database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)