from rest_framework import serializers, exceptions

from data_structures.feature_set import FeatureSet
from .element_set import ElementSetSerializer
from .feature import FeatureSerializer, NullableFeatureSerializer

class FeatureSetSerializer(ElementSetSerializer):

    elements = FeatureSerializer(required=False, many=True)

    def _build_set(self, data):
        '''
        A helper method which attempts to build a FeatureSet
        given the `data` arg. Assumes the `data` does have the 
        proper keys
        '''
        feature_list = []
        for feature_dict in data['elements']:
            # the validated data has the Feature info as an OrderedDict
            # below, we use the FeatureSerializer to turn that into
            # proper Feature instance.
            feature_serializer = FeatureSerializer(data=feature_dict)
            feat = feature_serializer.get_instance()
            feature_list.append(feat)
        fl = FeatureSet(
            feature_list, 
            data['multiple']
        )
        return fl

    def create(self, validated_data):
        '''
        Returns an FeatureSet instance from the validated
        data.
        '''
        return self._build_set(validated_data)

class NullableFeatureSetSerializer(FeatureSetSerializer):
    elements = NullableFeatureSerializer(required=False, many=True)
