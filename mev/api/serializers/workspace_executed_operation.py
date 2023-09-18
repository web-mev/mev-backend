from rest_framework import serializers, exceptions

from api.models import WorkspaceExecutedOperation, Operation, OperationCategory
from api.utilities.operations import get_operation_instance_data


class OperationField(serializers.RelatedField):
    def to_representation(self, value):

        # we need the operation input definitions to properly display
        # a summary when someone requests executed operations. This
        # way they can see the inputs used. For that, we need the 
        # operation data parsed from the op spec file:
        op_data = get_operation_instance_data(value)

        # for organizing the executed operations:
        OpCategories = OperationCategory.objects.filter(operation=value)
        categories = list(set([x.category for x in OpCategories]))
        return {
            'operation_id': str(value.id),
            'operation_name': value.name,
            'inputs': op_data['inputs'],
            'categories': categories,
            'active': value.active
        }

class WorkspaceExecutedOperationSerializer(serializers.ModelSerializer):
    operation = OperationField(many=False, read_only=True)

    class Meta:
        model = WorkspaceExecutedOperation
        fields = [
            'id',
            'owner',
            'workspace', 
            'operation',
            'job_id',
            'job_name',
            'inputs',
            'outputs',
            'error_messages', 
            'status',
            'execution_start_datetime',
            'execution_stop_datetime',
            'job_failed',
            'is_finalizing',
            'mode'
        ]