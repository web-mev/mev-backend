import logging
import uuid

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.models import Operation as OperationDbModel
from api.utilities.operations import get_operation_instance_data
from api.async_tasks.operation_tasks import ingest_new_operation \
     as async_ingest_new_operation


logger = logging.getLogger(__name__)


class OperationList(APIView):
    '''
    Lists available Operation instances.
    '''

    def get(self, request, *args, **kwargs):
        all_ops = OperationDbModel.objects.filter(active=True)
        op_list = []
        for op_model in all_ops:
            try:
                op_list.append(get_operation_instance_data(op_model))
            except Exception:
                return Response({}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(op_list)


class OperationDetail(APIView):
    '''
    Returns specific Operation instances. Note that we only permit GET operations
    as this is the only way users should be able to access the Operation table.
    Specific operations like modifications can only be performed by admins
    '''

    def get(self, request, *args, **kwargs):
        op_uuid = kwargs['operation_uuid']
        try:
            o = OperationDbModel.objects.get(id=op_uuid)
            if o.active:
                try:
                    data = get_operation_instance_data(o)
                    return Response(data)
                except Exception:
                    return Response({}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
                    f'Field "{field}"" is not valid.',
                    status=status.HTTP_400_BAD_REQUEST
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

        logger.info(
            f'POSTing to create a new Operation with data={request.data}')
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
            # We don't need the object itself, so we don't assign it to anything.
            # Note that we need git_commit to be non-null, so it gets assigned
            # an empty string (if the commit hash was not passed in the payload)
            OperationDbModel.objects.create(id=op_uuid,
                active=False,
                repository_url=url,
                git_commit=commit_id if commit_id else '')

            async_ingest_new_operation.delay(str(op_uuid), url, commit_id)
            return Response(
                {'operation_uuid': op_uuid},
                status=status.HTTP_200_OK
            )
        else:
            message = (f'The url {url} was not in our list of acceptable'
                       ' repository sources. Should be one of: '
                       f'{", ".join(settings.ACCEPTABLE_REPOSITORY_DOMAINS)}')
            return Response(
                {self.REPO_URL: message}, status=status.HTTP_400_BAD_REQUEST)
