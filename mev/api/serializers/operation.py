from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.data_structures import Operation
from api.serializers.operation_input import OperationInputSerializer
from api.serializers.operation_output import OperationOutputSerializer
from api.serializers.operation_input_dict import OperationInputDictSerializer
from api.serializers.operation_output_dict import OperationOutputDictSerializer

from api.runners import AVAILABLE_RUN_MODES

class OperationSerializer(serializers.Serializer):

    id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(max_length=5000, required=True)
    repository_url = serializers.URLField(required=True)
    git_hash = serializers.CharField(required=True)
    mode = serializers.CharField(max_length=100, required=True)
    inputs = OperationInputDictSerializer(required=True)
    outputs = OperationOutputDictSerializer(required=True)

    def validate_mode(self, mode):
        if not mode in AVAILABLE_RUN_MODES:
            raise ValidationError('The selected mode ({mode}) is invalid.'
                ' Please choose from among: {choices}'.format(
                    mode = mode,
                    choices = ', '.join(AVAILABLE_RUN_MODES)
                )
            )
        return mode

    def to_representation(self, instance):
        print(instance)
        print('*'*100)
        input_dict_rep = {}
        output_dict_rep = {}
        for key, item in instance.inputs.items():
            input_dict_rep[key] = OperationInputSerializer(item).data
        output_dict_rep = {}
        for key, item in instance.outputs.items():
            output_dict_rep[key] = OperationOutputSerializer(item).data
        return {
            'id': str(instance.id),
            'name': instance.name,
            'description': instance.description,
            'repository_url': instance.repository_url,
            'mode': instance.mode,
            'git_hash': instance.git_hash,
            'inputs': input_dict_rep,
            'outputs': output_dict_rep
        }

    def create(self, validated_data):
        '''
        Returns an Operation instance from the validated
        data.
        '''
        return Operation(validated_data['id'],
            validated_data['name'],
            validated_data['description'],
            validated_data['inputs'],
            validated_data['outputs'],
            validated_data['mode'],
            validated_data['repository_url'],
            validated_data['git_hash']
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