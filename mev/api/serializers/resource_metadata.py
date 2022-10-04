from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from constants import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    PARENT_OP_KEY

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

from api.models import ResourceMetadata, \
    Resource, \
    ExecutedOperation

class ResourceMetadataSerializer(serializers.ModelSerializer):

    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all()
    )
    # parent_operation = serializers.PrimaryKeyRelatedField(
    #     queryset=ExecutedOperation.objects.all(),
    #     many=True,
    #     allow_null=True
    # )
    observation_set = serializers.JSONField(allow_null=True)
    feature_set = serializers.JSONField(allow_null=True)

    # def _check_observation_set(self, obs_set_data):
    def validate_operation_set(self, obs_set_data):
        if obs_set_data is not None:
            try:
                ObservationSet(obs_set_data)
            except:
                raise ValidationError(
                    {OBSERVATION_SET_KEY: 'Invalid observation set'})
        return obs_set_data

    # def _check_feature_set(self, feature_set_data):
    def validate_feature_set(self, feature_set_data):
        if feature_set_data is not None:
            try:
                FeatureSet(feature_set_data)
            except:
                raise ValidationError(
                    {FEATURE_SET_KEY: 'Invalid feature set'})
        return feature_set_data

    # def create(self, validated_data):
    #     # check that the obs/featuresets are ok:
    #     self._check_observation_set(validated_data[OBSERVATION_SET_KEY])
    #     self._check_feature_set(validated_data[FEATURE_SET_KEY])

    #     rm = ResourceMetadata.objects.create(
    #         observation_set = validated_data[OBSERVATION_SET_KEY],
    #         feature_set = validated_data[FEATURE_SET_KEY],
    #         parent_operation = parent_op,
    #         resource = validated_data['resource']
    #     )
    #     return rm

    def update(self, instance, validated_data):
        # self._check_observation_set(validated_data[OBSERVATION_SET_KEY])
        # self._check_feature_set(validated_data[FEATURE_SET_KEY])
        instance.observation_set = obs_set_dict
        instance.feature_set = feature_set_dict
        instance.parent_operation = parent_op
        return instance

    def validate_parent_operation(self, value):
        if value is not None:
            try:
                ex_op = ExecutedOperation.objects.get(pk=value)
            except ExecutedOperation.DoesNotExist as ex:
                raise ValidationError({'parent_operation': 'Parent operation not found.'})
        return value

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