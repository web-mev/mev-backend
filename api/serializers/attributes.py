from rest_framework import serializers

import api.data_structures as api_ds
import api.exceptions as api_exceptions


class AttributeSerializer(serializers.BaseSerializer):

    def to_representation(self, instance):
        output = {}
        for key, attr_obj in instance.items():
            output[key] = attr_obj.to_representation()
        return output

    def to_internal_value(self, data):
        if type(data) != dict:
            raise serializers.ValidationError('Attributes must be '
                ' formatted as a mapping.  For example, {"phenotype":'
                ' <BaseAttribute>}')        
        for k in data.keys():
            attr_dict = data[k]
            api_ds.create_attribute(k, attr_dict)
            '''
            try:
                attr_val = attr_dict['value']
            except KeyError as ex:
                raise serializers.ValidationError({k: 'Attributes must supply'
                ' a "value" key.'})
            try:
                attribute_typename = attr_dict['attribute_type']
            except KeyError as ex:
                raise serializers.ValidationError({k: 'Attributes must supply'
                ' an "attribute_type" key.'})
        
            if not attribute_typename in api_ds.all_attribute_typenames:
                raise serializers.ValidationError({k:'Attributes must supply'
                ' a valid "attribute_type" from the choices of: {typelist}'.format(
                    typelist='\n'.join(api_ds.all_attribute_typenames)
                )})
            attribute_type = api_ds.attribute_mapping[attribute_typename]

            # we "test" validity by trying to create an Attribute subclass instance.
            # If the specification is not correct, it will raise an exception
            try:
                attribute_instance = attribute_type(attr_dict['value'])
            except serializers.ValidationError as ex:
                raise serializers.ValidationError({
                    k: ex.detail
                })
            '''
        return data

    def create(self, validated_data):
        final_attr_dict = {}
        for k in validated_data.keys():
            attr_dict = validated_data[k]
            attribute_type = api_ds.attribute_mapping[attr_dict['attribute_type']]
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