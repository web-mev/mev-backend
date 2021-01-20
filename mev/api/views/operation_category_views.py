import os
import logging
import uuid
from collections import defaultdict

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.models import OperationCategory, \
    Operation
from api.serializers.operation_category import OperationCategorySerializer
from api.serializers.operation import OperationSerializer
from api.utilities.operations import get_operation_instance_data

logger = logging.getLogger(__name__)


class OperationCategoryList(APIView):
    '''
    Returns a mapping of operation categories to the corresponding `Operation`s.
    Primarily used for populating a user-interface and grouping `Operation`s by
    their type.
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):
        
        all_records = OperationCategory.objects.all()
        results = defaultdict(list)
        for r in all_records:
            results[r.category].append(str(r.operation.pk))

        # reformat for tree-like structure
        response_payload = []
        for key in results.keys():
            child_list = []
            for op_pk in results[key]:
                op = Operation.objects.get(pk=op_pk)
                op_data = get_operation_instance_data(op)
                if op_data:
                    child_list.append(op_data)
            d = {'name': key, 'children': child_list}
            response_payload.append(d)
        return Response(response_payload)


class OperationCategoryDetail(APIView):
    '''
    Returns a list of the `Operation`s associated with the category
    passed as part of the url
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):
        category = self.kwargs['category']
        all_records = OperationCategory.objects.filter(category = category)
        results = []
        for r in all_records:
            op = Operation.objects.get(pk=r.operation_id)
            op_data = get_operation_instance_data(op)
            results.append(op_data)
        return Response(results)


class OperationCategoryAdd(APIView):

    permission_classes = [
        framework_permissions.IsAdminUser
    ]

    serializer_class = OperationCategorySerializer

    def post(self, request, *args, **kwargs):
        
        logger.info('POSTing to associate an Operation ({op_id}) with category "{cat}"'.format(
            op_id = request.data['operation_id'],
            cat = request.data['category']
        ))
        op_c_s = OperationCategorySerializer(data=request.data)
        if op_c_s.is_valid(raise_exception=True):
            data = op_c_s.validated_data
            op = Operation.objects.get(pk=data['operation_id'])
            o = OperationCategory.objects.create(
                operation=op,
                category = data['category']
            )
            return Response(status=status.HTTP_201_CREATED)