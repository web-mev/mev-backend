import logging

from rest_framework import generics
from rest_framework import permissions as framework_permissions
from rest_framework.exceptions import NotFound

from api.models import OperationResource, Operation
from api.serializers.operation_resource import OperationResourceSerializer

logger = logging.getLogger(__name__)

class OperationResourceList(generics.ListAPIView):
    '''
    Lists available OperationResource instances for
    a particular Operation. Includes the OperationResources
    for all fields    
    '''
    
    permission_classes = [framework_permissions.IsAuthenticated]

    serializer_class = OperationResourceSerializer

    def get_queryset(self):
        op_uuid = self.kwargs['operation_uuid']
        try:
            op = Operation.objects.get(pk=op_uuid)
            return OperationResource.objects.filter(operation=op)
        except Operation.DoesNotExist:
            raise NotFound()


class OperationResourceFieldList(generics.ListAPIView):
    '''
    Lists available OperationResource instances for
    a particular input field of Operation.
    '''
    
    permission_classes = [framework_permissions.IsAuthenticated]

    serializer_class = OperationResourceSerializer

    def get_queryset(self):
        op_uuid = self.kwargs['operation_uuid']
        input_field = self.kwargs['input_field']
        op = Operation.objects.get(pk=op_uuid)
        return OperationResource.objects.filter(
            operation=op,
            input_field=input_field    
        )