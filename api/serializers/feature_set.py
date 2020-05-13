from rest_framework import serializers, exceptions

from api.data_structures import FeatureSet
from .element_set import ElementSetSerializer
from api.serializers import FeatureSerializer

class FeatureSetSerializer(ElementSetSerializer):

    elements = FeatureSerializer(required=False, many=True)
        
    def create(self, validated_data):
        '''
        Returns an FeatureSet instance from the validated
        data.
        '''
        obs_list = []
        for obs_dict in validated_data['elements']:
            # the validated data has the Feature info as an OrderedDict
            # below, we use the FeatureSerializer to turn that into
            # proper Feature instance.
            obs_serializer = FeatureSerializer(data=obs_dict)
            obs = obs_serializer.get_instance()
            obs_list.append(obs)
        return FeatureSet(
            obs_list, 
            validated_data['multiple']
        )