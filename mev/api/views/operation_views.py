import os
import logging
import uuid

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.operation import OperationSerializer
from api.models import Operation as OperationDbModel
from api.utilities.operations import read_operation_json, \
    validate_operation, \
    get_operation_instance_data
from api.async_tasks.operation_tasks import ingest_new_operation as async_ingest_new_operation    


logger = logging.getLogger(__name__)

class OperationList(APIView):
    '''
    Lists available Operation instances.
    '''

    serializer_class = OperationSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        all_ops = OperationDbModel.objects.filter(active=True)
        uuid_set = [str(x.id) for x in all_ops]
        ret = []
        operation_dirs = os.listdir(settings.OPERATION_LIBRARY_DIR)
        for u in uuid_set:
            if u in operation_dirs:
                f = os.path.join(settings.OPERATION_LIBRARY_DIR, u, settings.OPERATION_SPEC_FILENAME)
                j = read_operation_json(f)
                op_serializer = validate_operation(j)
                ret.append(op_serializer.get_instance())
            else:
                logger.error('Integrity error: the queried Operation with'
                    ' id={uuid} did not have a corresponding folder.'.format(
                        uuid=u
                    )
                )
                return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        s = self.get_serializer(ret, many=True)
        return Response(s.data)

class OperationDetail(APIView):
    '''
    Returns specific Operation instances. Note that we only permit GET operations
    as this is the only way users should be able to access the Operation table.
    Specific operations like modifications can only be performed by admins
    '''

    serializer_class = OperationSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        op_uuid = kwargs['operation_uuid']
        try:
            o = OperationDbModel.objects.get(id=op_uuid)
            if o.active:
                data = get_operation_instance_data(o)
                if data:
                    return Response(data)
                else:            
                    return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({}, status=status.HTTP_404_NOT_FOUND)
        except OperationDbModel.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)


class OperationUpdate(APIView):
    '''
    Note that this method will NOT update aspects of the operation itself,
    such as the inputs, outputs, etc. as that breaks the principle that the
    operations are immutable once ingested. Rather, this only updates fields
    of the Operation database objects, which is more appropriately considered
    as metadata about the actual operation JSON object. For instance, you can
    use this endpoint to set the 'active' status, etc.
    '''

    permission_classes = [
        framework_permissions.IsAdminUser
    ]

    def patch(self, request, pk):
        db_object = OperationDbModel.objects.get(pk=pk)
        for field in request.data:
            if hasattr(db_object, field):
                setattr(db_object, field, request.data.get(field))
            else:
                return Response(
                    'Field {f} is not valid.'.format(f=field), 
                    status = status.HTTP_400_BAD_REQUEST
                )
        db_object.save()
        return Response({}, status=status.HTTP_200_OK)

class OperationCreate(APIView):

    REPO_URL = 'repository_url'
    COMMIT_ID = 'commit_id'

    permission_classes = [
        framework_permissions.IsAdminUser
    ]

    def post(self, request, *args, **kwargs):
        logger.info('POSTing to create a new Operation with data={data}'.format(
            data=request.data
        ))
        try:
            url = request.data[self.REPO_URL]
        except KeyError as ex:
            return Response({self.REPO_URL: 'You must supply this required key.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # can also check for a commit ID in case we don't want to use the default main.
        # It's optional, so just set to None if it is not specified. That will default
        # it to main
        try:
            commit_id = request.data[self.COMMIT_ID]
        except KeyError as ex:
            commit_id = None

        url_contents = url.split('/')
        domain = url_contents[2]
        if domain in settings.ACCEPTABLE_REPOSITORY_DOMAINS:

            # Create an Operation (database instance, not data structure) and set it to pending
            # while the ingestion happens.
            op_uuid = uuid.uuid4()
            db_op = OperationDbModel.objects.create(id=op_uuid, active=False)

            async_ingest_new_operation.delay(str(op_uuid), url, commit_id)
            return Response(
                {'operation_uuid': op_uuid},
                status=status.HTTP_200_OK
            )
        else:
            message = ('The url {url} was not in our list of acceptable repository sources.'
                ' Should be one of: {sources}'.format(
                    url = url,
                    sources=', '.join(settings.ACCEPTABLE_REPOSITORY_DOMAINS)
                )
            )
            return Response({self.REPO_URL: message}, status=status.HTTP_400_BAD_REQUEST)