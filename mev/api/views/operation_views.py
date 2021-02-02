import os
import logging
import uuid

from django.conf import settings

from rest_framework import generics
from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from api.serializers.operation import OperationSerializer
from api.serializers.executed_operation import ExecutedOperationSerializer
from api.serializers.workspace_executed_operation import WorkspaceExecutedOperationSerializer
from api.models import Operation as OperationDbModel
from api.models import Workspace, ExecutedOperation, WorkspaceExecutedOperation
import api.permissions as api_permissions
from api.utilities.operations import read_operation_json, \
    validate_operation, \
    validate_operation_inputs, \
    get_operation_instance_data
from api.async_tasks.operation_tasks import ingest_new_operation as async_ingest_new_operation    
from api.async_tasks.operation_tasks import submit_async_job, finalize_executed_op
from api.runners import get_runner

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


class ExecutedOperationList(APIView):
    '''
    Lists all the ExecutedOperations, both workspace and 
    non-workspace associated.

    Admins can list all, while other users can only see ExecutedOperations
    that they own
    '''
    permission_classes = [ 
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):

        user = request.user
        if user.is_staff:
            all_executed_operations = ExecutedOperation.objects.all()
            all_workspace_executed_operations = WorkspaceExecutedOperation.objects.all()
        else:
            all_executed_operations = ExecutedOperation.objects.filter(owner=user)
            all_workspace_executed_operations = WorkspaceExecutedOperation.objects.filter(owner=user)

        # want to show the Workspace for the workspace-associated operations. Querying ExecutedOperation
        # gets both, and we want to separate them out
        s1 = set([x.pk for x in all_executed_operations])
        s2 = set([x.pk for x in all_workspace_executed_operations])
        s3 = s1.difference(s2) # the set of UUIDs for the operations executed *outside* of workspaces

        # have to now segregate them out. Can't just iterate through all_executed_operations
        # since those are all of type ExecutedOperation (and hence don't have the workspace attr)
        response_payload = []
        for op in all_workspace_executed_operations:
            response_payload.append(WorkspaceExecutedOperationSerializer(op).data)
        for op in all_executed_operations:
            if op.pk in s3:
                response_payload.append(ExecutedOperationSerializer(op).data)
        return Response(response_payload, 
            status=status.HTTP_200_OK
        )



class WorkspaceExecutedOperationList(APIView):
    '''
    Lists available ExecutedOperation instances for a given Workspace.

    Admins can list all available executedOperations in a Workspace.
    
    Non-admin users can only view ExecutedOperations on Workspaces they own.
    '''
    NOT_FOUND_MESSAGE = 'No workspace found by ID: {id}'

    permission_classes = [ 
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):

        user = request.user

        # the UUID of the Workspace in which we are looking
        workspace_uuid = str(kwargs['workspace_pk'])

        try:
            workspace = Workspace.objects.get(pk=workspace_uuid)
        except Workspace.DoesNotExist as ex:
            return Response({'message': self.NOT_FOUND_MESSAGE.format(id=workspace_uuid)}, status=status.HTTP_404_NOT_FOUND)

        # check ownership via workspace. Users should only be able to query their own
        # analyses:
        if (user.is_staff) or (user == workspace.owner):
            executed_ops = WorkspaceExecutedOperation.objects.filter(workspace=workspace)
            response_payload = WorkspaceExecutedOperationSerializer(executed_ops, many=True).data
            return Response(response_payload, 
                status=status.HTTP_200_OK
            )
        else:
            return Response({'message': self.NOT_FOUND_MESSAGE.format(id=workspace_uuid)}, 
                status=status.HTTP_404_NOT_FOUND)


class ExecutedOperationCheck(APIView):
    '''
    Checks the status of an ExecutedOperation.

    If the ExecutedOperation is still running, nothing happens.
    If the ExecutedOperation has completed, runs some final steps, such as
    registering output files with the user, performing cleanup, etc.
    '''
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    NOT_FOUND_MESSAGE = 'No executed operation found by ID: {id}'

    def get(self, request, *args, **kwargs):

        logger.info('Requesting status of an ExecutedOperation.')

        user = request.user

        # the UUID of the ExecutedOperation
        exec_op_uuid = str(kwargs['exec_op_uuid'])

        try:
            matching_op = ExecutedOperation.objects.get(id=exec_op_uuid)
        except ExecutedOperation.DoesNotExist as ex:
            return Response({'message': self.NOT_FOUND_MESSAGE.format(id=exec_op_uuid)}, status=status.HTTP_404_NOT_FOUND)

        # check ownership. Users should only be able to query their own
        # analyses:
        owner = matching_op.owner
        if (user.is_staff) or (user == owner):
            if matching_op.execution_stop_datetime is None:
                logger.info('The stop time has not been set and job ({id})'
                    ' is still running or is finalizing.'.format(
                        id = exec_op_uuid
                    )
                )
                # if the stop time has not been set, the job is either still running
                # or it has completed, but not been "finalized"

                # first check if the "finalization" process has already been started.
                # If there are repeated requests to this endpoint, we don't want to trigger
                # multiple processes that "wrap-up" the analysis. Now, it is technically
                # possible for there to be a race condition if the query above is performed
                # before the database model can be updated and committed. No real way around 
                # that, except to avoid exceptionally rapid request intervals.
                if matching_op.is_finalizing:
                        logger.info('Currently finalizing job ({id})'.format(
                                id=exec_op_uuid
                            )
                        )
                        return Response(status=status.HTTP_208_ALREADY_REPORTED)
                else:
                    logger.info('No finalization process reported. Check job status.')
                    # not finalizing. Check if the job is running:
                    runner_class = get_runner(matching_op.mode)
                    runner = runner_class()
                    has_completed = runner.check_status(matching_op.job_id)
                    if has_completed:
                        logger.info('Job ({id}) has completed. Kickoff'
                            ' finalization.'.format(
                                id=exec_op_uuid
                            )
                        )
                        # kickoff the finalization. Set the flag for
                        # blocking multiple attempts to finalize.
                        matching_op.is_finalizing = True
                        matching_op.status = ExecutedOperation.FINALIZING
                        matching_op.save()
                        finalize_executed_op.delay(exec_op_uuid)
                        return Response(status=status.HTTP_202_ACCEPTED)
                    else: # job still running- just return no content
                        return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                response_payload = ExecutedOperationSerializer(matching_op).data
                
                if matching_op.job_failed:
                    logger.info('The requested job ({id}) failed.'.format(id=exec_op_uuid))
                else:
                    logger.info('The executed job was registered as completed. Return outputs.')
                    # analysis has completed and been finalized. return the outputs also

                return Response(response_payload, 
                    status=status.HTTP_200_OK
                )
        else:
            return Response({'message': self.NOT_FOUND_MESSAGE.format(id=exec_op_uuid)}, 
                status=status.HTTP_404_NOT_FOUND)

class OperationRun(APIView):
    '''
    Starts the execution of an Operation
    '''
    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    OP_UUID = 'operation_id'
    WORKSPACE_UUID = 'workspace_id'
    INPUTS = 'inputs'
    JOB_NAME = 'job_name'
    REQUIRED_KEYS = [OP_UUID, INPUTS]
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
        logger.info('Received payload of: {p}'.format(p=payload))
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

        # check workspace uuid if the Operation is required to be performed
        # in the context of a Workspace:
        if matching_op.workspace_operation:
            logger.info('A workspace-associated operation was requested.')
            try:
                workspace_uuid = uuid.UUID(payload[self.WORKSPACE_UUID])
            except KeyError as ex:
                return Response({self.WORKSPACE_UUID: 'Since the requested operation'
                        ' was intended to be run in the context of a Workspace, you'
                        ' must supply a workspace UUID in the payload.'
                    }, 
                    status=status.HTTP_400_BAD_REQUEST)
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
        else: # not a workspace operation-
            logger.info('A non-workspace operation was requested.')
            # need to set the workspace_uuid to None since we cannot pass
            # the database model instance to the async call.
            workspace_uuid = None

            # explicitly set the workspace to None so any workspace-related
            # checks are ignored in the input validation methods
            workspace = None

        # we can now validate the inputs:
        inputs = payload[self.INPUTS]
        if not (type(inputs) == dict):
            raise ValidationError({self.INPUTS: 'The "inputs"'
                ' key must be a JSON object.'
            })
        try:
            validated_inputs = validate_operation_inputs(request.user,
                inputs, matching_op, workspace)
        except ValidationError as ex:
            raise ValidationError({self.INPUTS: ex.detail})
        except Exception as ex:
            logger.error('Encountered some other exception when validating the user inputs.'
                ' The exception was: {ex}'.format(ex=ex)
            )
            raise ex

        # now that the inputs are validated against the spec, create an
        # ExecutedOperation instance and return it
        logger.info('Validated inputs: {v}'.format(v=validated_inputs))
        if validated_inputs is not None:
            dict_representation = {}
            for k,v in validated_inputs.items():
                if v:
                    dict_representation[k] = v.get_value()

            logger.info('dict representation of inputs: {d}'.format(d=dict_representation))

            # create the UUID which will identify the executed op.
            # We do this to avoid a race condition with the celery task queue.
            # In the past, the ExecutedOperation was created but the task was
            # invoked quickly enough that the database query could not find the
            # instance.
            executed_op_uuid = uuid.uuid4()

            # the job name can be explicitly assigned by the user, but otherwise
            # it will simply be the UUID of the job
            try:
                job_name = payload[self.JOB_NAME]
                if job_name is None:
                    job_name = str(executed_op_uuid)
            except KeyError as ex:
                job_name = str(executed_op_uuid)

            # send off the job
            submit_async_job.delay(
                executed_op_uuid, 
                matching_op.id,
                user.pk,
                workspace_uuid,
                job_name,
                dict_representation)

            return Response(
                {'executed_operation_id': str(executed_op_uuid)}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
