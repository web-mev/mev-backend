from api.data_structures import Feature
from api.serializers.element import BaseElementSerializer

class FeatureSerializer(BaseElementSerializer):
    '''
    Serializer for the `api.data_structures.Feature` class.
    '''
    def create(self, validated_data):
        '''
        Returns a Feature instance from the validated
        data.
        '''
        attr_dict = self._gather_attributes(validated_data)
        return Feature(validated_data['id'], attr_dict)
