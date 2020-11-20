from rest_framework import serializers, exceptions

from api.data_structures import ObservationSet
from .element_set import ElementSetSerializer
from .observation import ObservationSerializer, NullableObservationSerializer

class ObservationSetSerializer(ElementSetSerializer):

    elements = ObservationSerializer(required=False, many=True)
        
    def create(self, validated_data):
        '''
        Returns an ObservationSet instance from the validated
        data.
        '''
        obs_list = []
        for obs_dict in validated_data['elements']:
            # the validated data has the Observation info as an OrderedDict
            # below, we use the ObservationSerializer to turn that into
            # proper Observation instance.
            obs_serializer = ObservationSerializer(data=obs_dict)
            obs = obs_serializer.get_instance()
            obs_list.append(obs)
        return ObservationSet(
            obs_list, 
            validated_data['multiple']
        )

class NullableObservationSetSerializer(ObservationSetSerializer):
    elements = NullableObservationSerializer(required=False, many=True)