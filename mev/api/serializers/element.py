from rest_framework import serializers

from api.data_structures import create_attribute
from .attributes import AttributeSerializer, NullableAttributeSerializer


class BaseElementSerializer(serializers.Serializer):
    '''
    Serializer for the `api.data_structures.BaseElement` class
    and its derived children.
    '''

    # Prohibit identifiers for Elements to be longer than this
    MAX_LENGTH_ID = 100

    id = serializers.CharField()
    attributes = AttributeSerializer(required=False)

    def validate_id(self, id):
        if len(id) > self.MAX_LENGTH_ID:
            raise serializers.ValidationError('The identifier {x} must be shorter than {n}'.format(
                x = id,
                n = self.MAX_LENGTH_ID
            ))
        return id

    def validate(self, data):
        '''
        This is a final check on the deserialization where we can check
        validity on mulitple fields.  If the `Element` did not include
        any attributes, we simply fill-in an empty dict
        '''
        if not 'attributes' in data:
            data['attributes'] = {}
        return data

    def _gather_attributes(self, validated_data):
        '''
        This method is typically called by a child class such as 
        `ObservationSerializer`
        '''
        attr_dict = {}
        for k, v in validated_data['attributes'].items():
            if type(v) == dict:
                attr = create_attribute(k, v)
            else:
                attr = v
            attr_dict[k] = attr
        return attr_dict 

    def get_instance(self):
        '''
        A more suggestive way to retrieve the Element
        instance from the serializer than `save()`, since
        we are not actually saving Element instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        el = self.create(self.validated_data)
        return el


class NullableBaseElementSerializer(BaseElementSerializer):
    '''
    Specialization that allows the `attributes` dict to have 
    Attributes containing nulls.
    '''
    attributes = NullableAttributeSerializer(required=False)
