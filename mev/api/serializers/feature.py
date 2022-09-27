from data_structures.feature import Feature
from api.serializers.element import BaseElementSerializer, NullableBaseElementSerializer

class CreateMixin(object):
    def create(self, validated_data):
        '''
        Returns a Feature instance from the validated
        data.
        '''
        attr_dict = self._gather_attributes(validated_data)
        f = Feature(validated_data['id'], attr_dict)
        return f


class FeatureSerializer(CreateMixin, BaseElementSerializer):
    '''
    Serializer for the `api.data_structures.Feature` class.
    '''
    pass


class NullableFeatureSerializer(CreateMixin, NullableBaseElementSerializer):
    '''
    Serializer for the `api.data_structures.Feature` class.
    Allows the attributes field to have null values
    '''
    pass
