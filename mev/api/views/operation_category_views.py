import logging

from django.db.models import Count

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.models import OperationCategory, \
    Operation
from api.serializers.operation_category import OperationCategorySerializer, \
    OperationCategoryListSerializer
from api.utilities.operations import get_operation_instance_data
from api.views.mixins import SchemaMixin


logger = logging.getLogger(__name__)


class OperationCategoryList(APIView, SchemaMixin):
    '''
    Returns a mapping of operation categories to the corresponding `Operation`s.
    Primarily used for populating a user-interface and grouping `Operation`s by
    their type.
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    serializer_class = OperationCategoryListSerializer

    def get(self, request, *args, **kwargs):

        # no group-by directly, so we count and then rely on the serializer class
        # to make all the proper objects
        all_records = OperationCategory.objects.values('category').annotate(dcount=Count('category'))
        s = self.serializer_class(all_records, many=True)
        return Response(s.data)


class OperationCategoryDetail(APIView, SchemaMixin):
    '''
    Returns a list of the `Operation`s associated with the category
    passed as part of the url
    '''
    
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):
        category = self.kwargs['category']
        category_records = OperationCategory.objects.filter(category = category)
        ret = []
        for record in category_records:
            op_data = get_operation_instance_data(record.operation)
            if op_data is not None:
                ret.append(op_data)
            else:
                return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        return Response(ret)


class OperationCategoryAdd(APIView):
    '''
    Associates an `Operation` with a category. Organizing our tools/`Operation`s
    by category assists in the user interface.
    '''

    # Note that only admins can perform this request
    permission_classes = [
        framework_permissions.IsAdminUser
    ]

    serializer_class = OperationCategorySerializer

    def post(self, request, *args, **kwargs):
        
        logger.info('POSTing to associate an Operation'
            f' ({request.data["operation_id"]}) with category'
            f' {request.data["category"]}')
        op_c_s = OperationCategorySerializer(data=request.data)
        if op_c_s.is_valid(raise_exception=True):
            data = op_c_s.validated_data
            op = Operation.objects.get(pk=data['operation_id'])
            o = OperationCategory.objects.create(
                operation=op,
                category = data['category']
            )
            return Response(status=status.HTTP_201_CREATED)