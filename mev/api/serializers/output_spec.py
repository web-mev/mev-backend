import copy
from rest_framework.exceptions import ValidationError

from api.serializers.input_output_spec import InputOutputSpecSerializer

class OutputSpecSerializer(InputOutputSpecSerializer):
    '''
    Serializes/deserializes OutputSpec instances.
    '''

    def to_internal_value(self, data):
        output_spec_mapping = {}
        try:
            output_spec_type_str = data['attribute_type']
        except KeyError as ex:
            raise ValidationError('Need to supply an "attribute_type" key.')

        try:
            output_spec_type = output_spec_mapping[output_spec_type_str]
        except KeyError as ex:
            raise ValidationError('The "attribute_type" key does not reference a'
                ' valid type. Choices are: {choices}'.format(
                    choices=', '.join(output_spec_mapping.keys())
                ))
        # try to instantiate the underlying type as a way to validate.
        # If that fails, it will raise a ValidationError
        data_copy = copy.deepcopy(data)
        data_copy.pop('attribute_type')
        output_spec_type(**data_copy)
        return data

    def create(self, validated_data):
        data_copy = copy.deepcopy(validated_data)
        output_spec_type_str = data_copy.pop('attribute_type')
        output_spec_type = None
        return output_spec_type(**data_copy)