import os
import logging

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.operation import OperationSerializer
import api.permissions as api_permissions
from api.utilities.ingest_operation import read_operation_json, \
    validate_operation

logger = logging.getLogger(__name__)

class OperationList(APIView):
    '''
    Lists available Operation instances.
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    serializer_class = OperationSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        ret = []
        for d in os.listdir(settings.OPERATION_LIBRARY_DIR):
            f = os.path.join(settings.OPERATION_LIBRARY_DIR,d, settings.OPERATION_SPEC_FILENAME)
            j = read_operation_json(f)
            op_serializer = validate_operation(j)
            ret.append(op_serializer.get_instance())
        s = self.get_serializer(ret, many=True)
        return Response(s.data)

class OperationDetail(APIView):
    '''
    Returns specific Operation instances.
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    serializer_class = OperationSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        op_uuid = kwargs['operation_uuid']
        f = os.path.join(settings.OPERATION_LIBRARY_DIR, str(op_uuid), settings.OPERATION_SPEC_FILENAME)
        if os.path.exists(f):
            j = read_operation_json(f)
            op_serializer = validate_operation(j)
            s = self.get_serializer(op_serializer.get_instance())
            return Response(s.data)
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)