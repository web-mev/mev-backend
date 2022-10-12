from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.models import Operation, OperationCategory
from api.utilities.operations import get_operation_instance_data


class OperationCategorySerializer(serializers.Serializer):

    operation_id = serializers.UUIDField(required=True)
    category = serializers.CharField(max_length=100, required=True)

    def validate_operation_id(self, operation_id):
        try:
            op = Operation.objects.get(pk=operation_id)
            return operation_id
        except Operation.DoesNotExist as ex:
            raise ValidationError('Could not find Operation with'
                f' id={operation_id}'
            )


class OperationCategoryListSerializer(serializers.Serializer):

    name = serializers.CharField(max_length=200, read_only=True)
    children = serializers.JSONField()

    def to_representation(self, instance):
        category = instance['category']
        items = OperationCategory.objects.filter(category=category)
        child_list = []
        for item in items:
            op_pk = item.operation.pk
            op = Operation.objects.get(pk=op_pk)
            if op.active:
                op_data = get_operation_instance_data(op)
                if op_data:
                    child_list.append(op_data)
        d = {'name': category, 'children': child_list}
        return d