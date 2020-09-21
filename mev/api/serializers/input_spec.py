import copy
from rest_framework.exceptions import ValidationError

from api.data_structures.operation_input_spec import input_spec_mapping
from api.serializers.input_output_spec import InputOutputSpecSerializer

class InputSpecSerializer(InputOutputSpecSerializer):
    '''
    Serializes/deserializes InputSpec instances.
    '''

    def to_internal_value(self, data):
        data_copy = copy.deepcopy(data)
        try:
            input_spec_type_str = data_copy.pop('attribute_type')
        except KeyError as ex:
            raise ValidationError('Need to supply an "attribute_type" key.')

        try:
            input_spec_type = input_spec_mapping[input_spec_type_str]
        except KeyError as ex:
            raise ValidationError('The "attribute_type" key does not reference a'
                ' valid type. Choices are: {choices}'.format(
                    choices=', '.join(input_spec_mapping.keys())
                ))
        return input_spec_type(**data_copy)

    def create(self, validated_data):
        input_spec_type_str = validated_data.pop('attribute_type')
        input_spec_type = input_spec_mapping[input_spec_type_str]
        return input_spec_type(data=validated_data)