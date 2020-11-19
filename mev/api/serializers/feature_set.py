from rest_framework import serializers, exceptions

from api.data_structures import FeatureSet
from .element_set import ElementSetSerializer
from .feature import FeatureSerializer

class FeatureSetSerializer(ElementSetSerializer):

    elements = FeatureSerializer(required=False, many=True)
        
    def create(self, validated_data):
        '''
        Returns an FeatureSet instance from the validated
        data.
        '''
        feature_list = []
        for feature_dict in validated_data['elements']:
            # the validated data has the Feature info as an OrderedDict
            # below, we use the FeatureSerializer to turn that into
            # proper Feature instance.
            feature_serializer = FeatureSerializer(data=feature_dict)
            feat = feature_serializer.get_instance()
            feature_list.append(feat)
        return FeatureSet(
            feature_list, 
            validated_data['multiple']
        )