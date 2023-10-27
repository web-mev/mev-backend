import logging
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework import permissions as framework_permissions

from exceptions import WebMeVException

from api.serializers.executed_operation import ExecutedOperationSerializer
from api.serializers.workspace_executed_operation import WorkspaceExecutedOperationSerializer
from api.models import Operation as OperationDbModel
from api.models import Workspace, ExecutedOperation, WorkspaceExecutedOperation
from api.utilities.operations import validate_operation_inputs
from api.async_tasks.operation_tasks import submit_async_job
import api.permissions as api_permissions

logger = logging.getLogger(__name__)


def check_op(user, exec_op_uuid):

    try:
        matching_op = ExecutedOperation.objects.get(id=exec_op_uuid)
    except ExecutedOperation.DoesNotExist as ex:
        return None

    # check ownership. Users should only be able to query their own
    # analyses:
    if user == matching_op.owner:
        return matching_op


class ExecutedOperationList(APIView):
    '''
    Lists all the ExecutedOperations, both workspace and 
    non-workspace associated.
    '''

    def get(self, request, *args, **kwargs):

        user = request.user
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


class NonWorkspaceExecutedOperationList(APIView):
    '''
    Lists all the ExecutedOperations not associated with a workspace
    '''

    def get(self, request, *args, **kwargs):

        user = request.user
        all_executed_operations = ExecutedOperation.objects.filter(owner=user)

        # Since ExecutedOperation is a superset of WorkspaceExecutedOperation
        # we need to iterate through and skip the workspace-associated objects.
        response_payload = []
        for exec_op in all_executed_operations:
            op = exec_op.operation
            if not op.workspace_operation:
                response_payload.append(ExecutedOperationSerializer(exec_op).data)
        return Response(response_payload, 
            status=status.HTTP_200_OK
        )


class WorkspaceExecutedOperationList(APIView):
    '''
    Lists available ExecutedOperation instances for a given Workspace.
    '''
    NOT_FOUND_MESSAGE = 'No workspace found by ID: {id}'

    def get(self, request, *args, **kwargs):

        user = request.user

        # the UUID of the Workspace in which we are looking
        workspace_uuid = str(kwargs['workspace_pk'])

        try:
            workspace = Workspace.objects.get(pk=workspace_uuid)
        except Workspace.DoesNotExist as ex:
            return Response(
                {'message': self.NOT_FOUND_MESSAGE.format(id=workspace_uuid)}, 
                status=status.HTTP_404_NOT_FOUND)

        # check ownership via workspace. Users should only be able to query their own
        # analyses:
        if user == workspace.owner:
            executed_ops = WorkspaceExecutedOperation.objects.filter(workspace=workspace)
            response_payload = WorkspaceExecutedOperationSerializer(
                executed_ops, many=True).data
            return Response(response_payload, 
                status=status.HTTP_200_OK
            )
        else:
            # Don't give any information about whether the workspace exists or not if
            # the user is not the owner.
            return Response({'message': self.NOT_FOUND_MESSAGE.format(id=workspace_uuid)}, 
                status=status.HTTP_404_NOT_FOUND)


class ExecutedOperationCheck(APIView):
    '''
    Checks the status of an ExecutedOperation.

    If the ExecutedOperation is still running, nothing happens.
    If the ExecutedOperation has completed, runs some final steps, such as
    registering output files with the user, performing cleanup, etc.

    Note that there is a celery task that pings the job status and sets
    the various fields on the `Operation` instance. This view simply
    reads that and returns a status code indicating that current job state.
    '''

    permission_classes = [api_permissions.IsOwner & framework_permissions.IsAuthenticated]

    NOT_FOUND_MESSAGE = 'No executed operation found by ID: {id}'

    def get(self, request, *args, **kwargs):

        logger.info('Requesting status of an ExecutedOperation.')

        user = request.user

        # the UUID of the ExecutedOperation
        exec_op_uuid = str(kwargs['exec_op_uuid'])

        matching_op = check_op(user, exec_op_uuid)
        if matching_op is None:
            return Response(
                {'message': self.NOT_FOUND_MESSAGE.format(id=exec_op_uuid)}, 
                status=status.HTTP_404_NOT_FOUND)

        if matching_op.execution_stop_datetime is None:
            logger.info('The stop time has not been set'
                f' and job ({exec_op_uuid}) is still'
                ' running or is finalizing.')

            # if the stop time has not been set, the job is either still running
            # or it has completed, but not been "finalized"

            # first check if the "finalization" process has already been started.
            # The finalization can sometimes take some time, so there is a short
            # period of time between the analysis completion and the data being ready.
            if matching_op.is_finalizing:
                    logger.info(f'Currently finalizing job ({exec_op_uuid})')
                    return Response(status=status.HTTP_208_ALREADY_REPORTED)
            else:
                logger.info('No finalization process reported. Job still running.')
                # not finalizing. The job is still running:
                return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            response_payload = ExecutedOperationSerializer(matching_op).data
            
            if matching_op.job_failed:
                logger.info(f'The requested job ({exec_op_uuid}) failed.')
            else:
                logger.info('The executed job was registered as completed. Return outputs.')
                # analysis has completed and been finalized. return the outputs also

            return Response(response_payload, 
                status=status.HTTP_200_OK
            )


class OperationRun(APIView):
    '''
    Starts the execution of an Operation
    '''

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
        logger.info(f'POSTing to run an Operation with data={request.data}')

        user = request.user
        payload = request.data
        logger.info(f'Received payload of: {payload}')

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

        # Get the `Operation` instance. This catches both the case 
        # where the UUID is malformatted (400) or not found (404)
        op_uuid = payload[self.OP_UUID]
        try:
            matching_ops = OperationDbModel.objects.filter(id=op_uuid)
            if len(matching_ops) != 1:
                message = (f'Operation ID: {op_uuid} did not'
                    ' match any known operations')
                return Response({self.OP_UUID: message}, 
                    status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError:
            message = self.BAD_UUID_MESSAGE.format(
                field=self.OP_UUID,
                uuid=payload[self.OP_UUID]
            )
            return Response({self.OP_UUID: message}, 
                status=status.HTTP_400_BAD_REQUEST)
        
        # If we are here, we have a valid `Operation` instance
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

            # ensure that there is a Workspace corresponding to that UUID
            # AND that it is owned by teh requesting user
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
        # catches data structure format exceptions, etc.
        except WebMeVException as ex:
            raise ValidationError({self.INPUTS: str(ex)})
        except Exception as ex:
            logger.error('Encountered some other exception when validating'
                f' the user inputs. The exception was: {ex}')
            raise ex

        # now that the inputs are validated against the spec, create an
        # ExecutedOperation instance and return it
        logger.info(f'Validated inputs: {validated_inputs}')
        if validated_inputs is not None:
            dict_representation = {}
            for k,v in validated_inputs.items():
                if v is not None:
                    dict_representation[k] = v

            logger.info(f'dict repr of inputs: {dict_representation}')

            # create the UUID which will identify the executed op.
            # We do this to avoid a race condition with the celery task queue.
            # In the past, the ExecutedOperation was created but the task was
            # invoked quickly enough that the database query could not find the
            # instance.
            executed_op_uuid = uuid.uuid4()

            # the job name can be explicitly assigned by the user, but otherwise
            # it will simply be the UUID of the job
            try:
                job_name = str(payload[self.JOB_NAME]) # add string cast since numbers can be passed
                job_name = job_name.strip() 

                if (job_name is None) or (len(job_name) == 0):
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


class ExecutedOperationResultsQuery(APIView):
    pass