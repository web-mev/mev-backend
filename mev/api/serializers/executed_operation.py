from rest_framework import serializers, exceptions

from api.models import ExecutedOperation

class ExecutedOperationSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExecutedOperation
        fields = '__all__'