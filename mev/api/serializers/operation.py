from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.data_structures import Operation
from api.serializers.operation_input_dict import OperationInputDictSerializer
from api.serializers.operation_output_dict import OperationOutputDictSerializer
from api.runners import AVAILABLE_RUNNERS


class OperationSerializer(serializers.Serializer):

    id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(max_length=5000, required=True)
    repository_url = serializers.URLField(required=True, allow_blank=True)
    git_hash = serializers.CharField(required=True, allow_blank=True)
    mode = serializers.CharField(max_length=100, required=True)
    inputs = OperationInputDictSerializer(required=True)
    outputs = OperationOutputDictSerializer(required=True)
    repo_name = serializers.CharField(required=True, allow_blank=True)
    workspace_operation = serializers.BooleanField(required=True)

    def validate_mode(self, mode):
        if not mode in AVAILABLE_RUNNERS:
            raise ValidationError('The selected mode ({mode}) is invalid.'
                ' Please choose from among: {choices}'.format(
                    mode = mode,
                    choices = ', '.join(AVAILABLE_RUNNERS)
                )
            )

    def to_representation(self, instance):
        return instance.to_dict()

    def create(self, validated_data):
        '''
        Returns an Operation instance from the validated
        data.
        '''
        input_obj = OperationInputDictSerializer(data=validated_data['inputs']).get_instance()
        output_obj = OperationOutputDictSerializer(data=validated_data['outputs']).get_instance()
        return Operation(validated_data['id'],
            validated_data['name'],
            validated_data['description'],
            input_obj,
            output_obj,
            validated_data['mode'],
            validated_data['repository_url'],
            validated_data['git_hash'],
            validated_data['repo_name'],
            validated_data['workspace_operation']
        )

    def get_instance(self):
        '''
        A more suggestive way to retrieve the Operation
        instance from the serializer than `save()`, since
        we are not actually saving Operation instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)