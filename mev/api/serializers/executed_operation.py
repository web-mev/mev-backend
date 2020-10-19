from rest_framework import serializers, exceptions

from api.models import ExecutedOperation, Operation

class OperationField(serializers.RelatedField):
    def to_representation(self, value):
        return value.name

class ExecutedOperationSerializer(serializers.ModelSerializer):
    operation = OperationField(many=False, read_only=True)

    class Meta:
        model = ExecutedOperation
        fields = [
            'id', 
            'workspace', 
            'operation',
            'job_id',
            'job_name',
            'inputs',
            'outputs',
            'error_message', 
            'status',
            'execution_start_datetime',
            'execution_stop_datetime',
            'job_failed',
            'is_finalizing',
            'mode'
        ]