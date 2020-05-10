from rest_framework import serializers

import api.data_structures as api_ds
import api.exceptions as api_exceptions


class AttributeSerializer(serializers.BaseSerializer):

    def to_representation(self, instance):
        # instance is a subclass of api.data_structures.attributes.BaseAttribute

        output = {}
        output['key'] = instance.key
        output['attribute_type'] = instance.typename
        output['value'] = instance.value
        return output

    def to_internal_value(self, data):
        
        try:
            attribute_typename = data['attribute_type']
        except KeyError as ex:
            raise serializers.ValidationError('Attributes must supply'
            ' an "attribute_type" key.')
        
        if not attribute_typename in api_ds.all_attribute_typenames:
            raise serializers.ValidationError('Attributes must supply'
            ' a valid "attribute_type" from the choices of: {typelist}'.format(
                typelist='\n'.join(api_ds.all_attribute_typenames)
            ))

        attribute_type = api_ds.attribute_mapping[attribute_typename]
        try:
            attribute_instance = attribute_type(data['key'], data['value'])
        except api_exceptions.AttributeException as ex:
            raise ex
        return attribute_instance
