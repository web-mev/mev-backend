from rest_framework import serializers, exceptions

from data_structures.observation_set import ObservationSet
from .element_set import ElementSetSerializer
from .observation import ObservationSerializer, NullableObservationSerializer

class ObservationSetSerializer(ElementSetSerializer):

    elements = ObservationSerializer(required=False, many=True)
        
    def _build_set(self, data):
        '''
        A helper method which attempts to build an ObservationSet
        given the `data` arg. Assumes the `data` does have the 
        proper keys
        '''
        obs_list = []
        for obs_dict in data['elements']:
            obs_serializer = ObservationSerializer(data=obs_dict)
            obs = obs_serializer.get_instance()
            obs_list.append(obs)
        return ObservationSet(
            obs_list, 
            data['multiple']
        )

    def create(self, validated_data):
        '''
        Returns an ObservationSet instance from the validated
        data.
        '''
        return self._build_set(validated_data)

class NullableObservationSetSerializer(ObservationSetSerializer):
    elements = NullableObservationSerializer(required=False, many=True)
