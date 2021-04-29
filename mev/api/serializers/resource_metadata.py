from rest_framework import serializers, exceptions

from api.models import ResourceMetadata, \
    Resource, \
    ExecutedOperation

from api.serializers.observation_set import NullableObservationSetSerializer
from api.serializers.feature_set import NullableFeatureSetSerializer

class ResourceMetadataSerializer(serializers.ModelSerializer):

    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all()
    )
    observation_set = NullableObservationSetSerializer(required=False, allow_null=True)
    feature_set = NullableFeatureSetSerializer(required=False, allow_null=True)

    def prep_validated_data(self, validated_data):
        '''
        This method is used by the create and update methods
        to create the proper serialized elements
        '''

        # the database object is saving json. Hence, we need to turn the 
        # observationSet into a dict to create/update the ResourceMetadata below.
        try:
            obs_set_data = validated_data['observation_set']
        except KeyError as ex:
            obs_set_data = None
        if obs_set_data:
            obs_set_serializer = NullableObservationSetSerializer(data=obs_set_data)
            obs_set = obs_set_serializer.get_instance()
            obs_set_dict = obs_set.to_dict()
        else:
            obs_set_dict = None

        # same thing for the FeatureSet- need a dict
        try:
            feature_set_data = validated_data['feature_set']
        except KeyError as ex:
            feature_set_data = None
        if feature_set_data:
            feature_set_serializer = NullableFeatureSetSerializer(data=validated_data['feature_set'])
            feature_set = feature_set_serializer.get_instance()
            feature_set_dict = feature_set.to_dict()
        else:
            feature_set_dict = None

        try:
            parent_op = validated_data['parent_operation']
        except KeyError as ex:
            parent_op = None
        if parent_op is not None:
            parent_op = ExecutedOperation.objects.get(pk=parent_op)

        return obs_set_dict, feature_set_dict, parent_op

    def create(self, validated_data):
        obs_set_dict, feature_set_dict, parent_op = self.prep_validated_data(validated_data)
        rm = ResourceMetadata.objects.create(
            observation_set = obs_set_dict,
            feature_set = feature_set_dict,
            parent_operation = parent_op,
            resource = validated_data['resource']
        )
        return rm

    def update(self, instance, validated_data):
        obs_set_dict, feature_set_dict, parent_op = self.prep_validated_data(validated_data)
        instance.observation_set = obs_set_dict
        instance.feature_set = feature_set_dict
        instance.parent_operation = parent_op
        return instance

    def validate_parent_operation(self, value):
        if value is not None:
            try:
                ExecutedOperation.objects.get(pk=value)
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