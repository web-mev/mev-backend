import os
import logging
import uuid

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.serializers.operation import OperationSerializer
from api.models import Operation as OperationDbModel
from api.models import Workspace
import api.permissions as api_permissions
from api.utilities.operations import read_operation_json, \
    validate_operation, \
    validate_operation_inputs, \
    get_operation_instance_data
from api.async_tasks import ingest_new_operation as async_ingest_new_operation    

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


class OperationCreate(APIView):

    REPO_URL = 'repository_url'

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
        url_contents = url.split('/')
        domain = url_contents[2]
        if domain in settings.ACCEPTABLE_REPOSITORY_DOMAINS:

            # Create an Operation (database instance, not data structure) and set it to pending
            # while the ingestion happens.
            op_uuid = uuid.uuid4()
            db_op = OperationDbModel.objects.create(id=op_uuid, active=False)

            async_ingest_new_operation.delay(str(op_uuid), url)
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


class OperationRun(APIView):

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    OP_UUID = 'operation_id'
    WORKSPACE_UUID = 'workspace_id'
    INPUTS = 'inputs'
    REQUIRED_KEYS = [OP_UUID, WORKSPACE_UUID, INPUTS]
    REQUIRED_MESSAGE = 'This field is required.'
    BAD_UUID_MESSAGE = ('{field}: {uuid} could not'
        ' be cast as a valid UUID')
    NOT_FOUND_MESSAGE = ('An instance with identifier {uuid}'
        ' was not found.')

    def post(self, request, *args, **kwargs):
        logger.info('POSTing to run an Operation with data={data}'.format(
            data=request.data
        ))

        payload = request.data
        user = request.user

        # first check that all the proper keys are present
        # in the payload
        missing_keys = []
        for k in self.REQUIRED_KEYS:
            try:
                payload[k]
            except KeyError as ex:
                missing_keys.append(k)
                
        if len(missing_keys) > 0:
            response_payload = {}
            for k in missing_keys:
                response_payload[k] = self.REQUIRED_MESSAGE
            return Response(response_payload, 
                status=status.HTTP_400_BAD_REQUEST)

        # check that the operation_id was indeed a valid operation.
        try:
            op_uuid = uuid.UUID(payload[self.OP_UUID])
        except Exception as ex:
            message = self.BAD_UUID_MESSAGE.format(
                field=self.OP_UUID,
                uuid=payload[self.OP_UUID]
            )
            return Response({self.OP_UUID: message}, 
                status=status.HTTP_400_BAD_REQUEST)
        
        # ok, so the op_uuid was indeed a valid UUID. Does it match anything?
        matching_ops = OperationDbModel.objects.filter(id=op_uuid)
        if len(matching_ops) != 1:
            message = ('Operation ID: {op_uuid} did not'
                ' match any known operations'.format(
                    op_uuid=op_uuid
                )
            )
            return Response({self.OP_UUID: message}, 
                status=status.HTTP_404_NOT_FOUND)
        matching_op = matching_ops[0]

        # check workspace uuid:
        try:
            workspace_uuid = uuid.UUID(payload[self.WORKSPACE_UUID])
        except Exception as ex:
            message = self.BAD_UUID_MESSAGE.format(
                field=self.WORKSPACE_UUID,
                uuid=payload[self.WORKSPACE_UUID]
            )
            return Response({self.WORKSPACE_UUID: message}, 
                status=status.HTTP_400_BAD_REQUEST)

        # ensure that there is a Workspace corresponding to that UUID:
        try:
            workspace = Workspace.objects.get(id=workspace_uuid, owner=user)
        except Workspace.DoesNotExist:
            message = self.NOT_FOUND_MESSAGE.format(
                uuid=payload[self.WORKSPACE_UUID]
            )
            return Response({self.WORKSPACE_UUID: message}, 
                status=status.HTTP_404_NOT_FOUND)

        # we can now validate the inputs:
        inputs = payload[self.INPUTS]
        try:
            inputs_are_valid = validate_operation_inputs(request.user,
                inputs, matching_op, workspace)
        except ValidationError as ex:
            raise ValidationError({self.INPUTS: ex.detail})

        # now that the inputs are validated against the spec, create an
        # ExecutedOperation instance and return it
        if inputs_are_valid:
            # temporary:
            u = uuid.uuid4()
            # TODO: create ExecutedOp
            # TODO: submit to runner
            return Response({'executed_operation_id': str(u)}, status=status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
