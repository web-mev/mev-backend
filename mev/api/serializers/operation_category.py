from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.models import Operation

class OperationCategorySerializer(serializers.Serializer):

    operation_id = serializers.UUIDField(required=True)
    category = serializers.CharField(max_length=100, required=True)

    def validate_operation_id(self, operation_id):
        try:
            op = Operation.objects.get(pk=operation_id)
            return operation_id
        except Operation.DoesNotExist as ex:
            raise ValidationError('Could not find Operation with'
                ' id={id}'.format(id=operation_id)
            )