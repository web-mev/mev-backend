import copy

from rest_framework.exceptions import ValidationError

from api.exceptions import AttributeValueError
from api.data_structures.operation_input_spec import input_spec_mapping
from api.serializers.input_output_spec import InputOutputSpecSerializer

class InputSpecSerializer(InputOutputSpecSerializer):
    '''
    Serializes/deserializes InputSpec instances.
    '''

    def to_internal_value(self, data):
        try:
            input_spec_type_str = data['attribute_type']
        except KeyError as ex:
            raise ValidationError('Need to supply an "attribute_type" key.')

        try:
            input_spec_type = input_spec_mapping[input_spec_type_str]
        except KeyError as ex:
            raise ValidationError('The "attribute_type" key does not reference a'
                ' valid type. Choices are: {choices}'.format(
                    choices=', '.join(input_spec_mapping.keys())
                ))
        # try to instantiate the underlying type as a way to validate.
        # If that fails, it will raise a ValidationError
        data_copy = copy.deepcopy(data)
        data_copy.pop('attribute_type')
        input_spec_type(**data_copy)
        return data

    def create(self, validated_data):
        data_copy = copy.deepcopy(validated_data)
        input_spec_type_str = data_copy.pop('attribute_type')
        input_spec_type = input_spec_mapping[input_spec_type_str]
        return input_spec_type(**data_copy)