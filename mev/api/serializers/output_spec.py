from rest_framework.exceptions import ValidationError

import api.data_structures as api_ds
from api.serializers.input_output_spec import InputOutputSpecSerializer

class OutputSpecSerializer(InputOutputSpecSerializer):
    '''
    Serializes/deserializes OutputSpec instances.
    '''

    def to_internal_value(self, data):
        try:
            input_spec_type_str = data.pop('attribute_type')
        except KeyError as ex:
            raise ValidationError('Need to supply an "attribute_type" key.')

        try:
            input_spec_type = api_ds.operation_output.output_spec_mapping[input_spec_type_str]
        except KeyError as ex:
            raise ValidationError('The "attribute_type" key does not reference a'
                ' valid type. Choices are: {choices}'.format(
                    choices=', '.join(api_ds.operation_output.output_spec_mapping.keys())
                ))
        return input_spec_type(**data)

    def create(self, validated_data):
        input_spec_type_str = validated_data.pop('attribute_type')
        input_spec_type = api_ds.operation_output.output_spec_mapping[input_spec_type_str]
        return input_spec_type(data=validated_data)