from rest_framework import serializers

from api.utilities import normalize_identifier
from api.data_structures import create_attribute
from .attributes import AttributeSerializer


class BaseElementSerializer(serializers.Serializer):
    '''
    Serializer for the `api.data_structures.BaseElement` class
    and its derived children.
    '''
    id = serializers.CharField(max_length=50)
    attributes = AttributeSerializer(required=False)

    def validate_id(self, id):
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
        for k, val_dict in validated_data['attributes'].items():
            attr = create_attribute(k, val_dict)
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
        return self.create(self.validated_data)
