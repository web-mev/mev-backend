from rest_framework import serializers, exceptions

from api.data_structures import Observation, create_attribute
from api.utilities import normalize_identifier
from api.exceptions import StringIdentifierException
from .attributes import AttributeSerializer


class ObservationSerializer(serializers.Serializer):
    '''
    Serializer for the `api.data_structures.Observation` class.
    '''
    id = serializers.CharField(max_length=50)
    attributes = AttributeSerializer(required=False)

    def validate_id(self, id):
        normalized_id = normalize_identifier(id)
        return normalized_id

    def validate(self, data):
        '''
        This is a final check on the deserialization where we can check
        for things like duplicate attribute keys, etc.
        '''
        if not 'attributes' in data:
            data['attributes'] = {}
        return data

    def create(self, validated_data):
        '''
        Returns an Observation instance from the validated
        data.
        '''
        attr_dict = {}
        for k, val_dict in validated_data['attributes'].items():
            attr = create_attribute(k, val_dict)
            attr_dict[k] = attr
        return Observation(validated_data['id'], attr_dict)

    def get_instance(self):
        '''
        A more suggestive way to retrieve the Observation
        instance from the serializer than `save()`, since
        we are not actually saving Observation instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)
