from api.data_structures import Observation
from api.serializers.element import BaseElementSerializer

class ObservationSerializer(BaseElementSerializer):
    '''
    Serializer for the `api.data_structures.Observation` class.
    '''
    def create(self, validated_data):
        '''
        Returns an Observation instance from the validated
        data.
        '''
        attr_dict = self._gather_attributes(validated_data)
        return Observation(validated_data['id'], attr_dict)
