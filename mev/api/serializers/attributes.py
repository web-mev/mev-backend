from rest_framework import serializers

import api.data_structures as api_ds
import api.exceptions as api_exceptions


class AttributeSerializer(serializers.BaseSerializer):
    '''
    Serializes/deserializes attributes.  Observation instances
    contain attribute dictionaries.  The keys of those dicts 
    are a unique set of string identifiers and the values are 
    sub-classes of api.data_structures.attributes.BaseAttribute
    '''

    def to_representation(self, instance):
        output = {}
        for key, attr_obj in instance.items():
            if type(attr_obj) == dict:
                output[key] = attr_obj
            else:
                output[key] = attr_obj.to_representation()
        return output

    def to_internal_value(self, data):
        if type(data) != dict:
            raise serializers.ValidationError('Attributes must be '
                ' formatted as a mapping.  For example, {"phenotype":'
                ' <BaseAttribute>}')  
        for k in data.keys():
            v = data[k]
            if type(v) == dict:
                v=api_ds.create_attribute(k, v)
            data[k]=v
        return data

    def create(self, validated_data):
        final_attr_dict = {}
        for k in validated_data.keys():
            attr_dict = validated_data[k]
            attribute_type = api_ds.attributes.attribute_mapping[attr_dict['attribute_type']]
            attribute_instance = attribute_type(attr_dict['value'])
            final_attr_dict[k] = attribute_instance
        return final_attr_dict

    def get_instance(self):
        '''
        The `save` method of serializers could work here, but this 
        naming is more suggestive since we are not actually saving attributes
        to any database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)