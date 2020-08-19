from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import api.data_structures as api_ds


class InputSpecSerializer(serializers.BaseSerializer):
    '''
    Serializes/deserializes InputSpec instances.
    '''

    def to_representation(self, instance):
        return instance.to_representation()

    def to_internal_value(self, data):
        try:
            input_spec_type_str = data.pop('attribute_type')
        except KeyError as ex:
            raise ValidationError('Need to supply an "attribute_type" key.')

        try:
            input_spec_type = api_ds.operation_input.input_spec_mapping[input_spec_type_str]
        except KeyError as ex:
            raise ValidationError('The "attribute_type" key does not reference a'
                ' valid type. Choices are: {choices}'.format(
                    choices=', '.join(api_ds.operation_input.input_spec_mapping.keys())
                ))
        return input_spec_type(**data)

    def create(self, validated_data):
        input_spec_type_str = validated_data.pop('attribute_type')
        input_spec_type = api_ds.operation_input.input_spec_mapping[input_spec_type_str]
        return input_spec_type(data=validated_data)

    def get_instance(self):
        '''
        The `save` method of serializers could work here, but this 
        naming is more suggestive since we are not actually saving
        to any database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)