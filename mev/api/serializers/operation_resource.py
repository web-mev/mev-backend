import logging

from api.models import OperationResource
from api.serializers.resource import ResourceSerializer

logger = logging.getLogger(__name__)

class OperationResourceSerializer(ResourceSerializer):

    class Meta(ResourceSerializer.Meta):
        model = OperationResource
        fields = [
            'id',
            'name',
            'input_field',
            'operation',
            'resource_type',
            'datafile',
            'size',
            'readable_resource_type'
        ]