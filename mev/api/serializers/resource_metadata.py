from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from constants import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    PARENT_OP_KEY

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

from api.models import ResourceMetadata, \
    Resource

class ResourceMetadataSerializer(serializers.ModelSerializer):

    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all()
    )
    observation_set = serializers.JSONField(allow_null=True, default=None)
    feature_set = serializers.JSONField(allow_null=True, default=None)

    def validate_observation_set(self, obs_set_data):
        if obs_set_data is not None:
            try:
                o = ObservationSet(obs_set_data)
                return o.to_simple_dict()
            except Exception as ex:
                raise ValidationError(f'Invalid observation set: {ex}')
        return obs_set_data

    def validate_feature_set(self, feature_set_data):
        if feature_set_data is not None:
            try:
                f = FeatureSet(feature_set_data)
                return f.to_simple_dict()
            except Exception as ex:
                raise ValidationError(f'Invalid feature set: {ex}')
        return feature_set_data

    def create(self, validated_data):
        try:
            parent_operation = validated_data[PARENT_OP_KEY]
        except KeyError as ex:
            parent_operation = None

        rm = ResourceMetadata.objects.create(
            observation_set=validated_data[OBSERVATION_SET_KEY],
            feature_set=validated_data[FEATURE_SET_KEY],
            parent_operation=parent_operation,
            resource=validated_data[RESOURCE_KEY]
        )
        return rm

    def update(self, instance, validated_data):
        instance.observation_set = validated_data[OBSERVATION_SET_KEY]
        instance.feature_set = validated_data[FEATURE_SET_KEY]
        try:
            parent_operation = validated_data[PARENT_OP_KEY]
        except KeyError as ex:
            parent_operation = None
        instance.parent_operation = parent_operation
        return instance

    class Meta:
        model = ResourceMetadata
        fields = [
            'resource',
            'parent_operation',
            'observation_set',
            'feature_set'
        ]

class ResourceMetadataObservationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceMetadata
        fields = ['observation_set',]

class ResourceMetadataFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceMetadata
        fields = ['feature_set',]

class ResourceMetadataParentOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceMetadata
        fields = ['parent_operation',]