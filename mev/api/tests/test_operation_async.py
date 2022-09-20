import unittest
import unittest.mock as mock
import uuid


from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from api.tests.base import BaseAPITestCase
from api.models import ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Operation, \
    Workspace
from api.async_tasks.operation_tasks import finalize_executed_op

class OperationAsyncTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.async_tasks.operation_tasks.finalize_job')
    @mock.patch('api.async_tasks.operation_tasks.get_operation_instance_data')
    def test_gets_correct_op_type(self, 
        mock_get_operation_instance_data, 
        mock_finalize_job):
        '''
        Tests that the proper type of ExecutedOperation is 
        passed to the finalization methods.

        Recall that we can have operations that are executed with or without
        an association with a workspace. To properly associate files with the
        workspace, we need to ensure the proper type is passed to the
        finalization functions
        '''
        # add a workspace and a non-workspace operation:
        op_uuid = uuid.uuid4()
        op = Operation.objects.create(id=str(op_uuid))

        # need a user's workspace to create an ExecutedOperation
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        workspace = user_workspaces[0]

        # create a mock ExecutedOperation
        workspace_exec_op_uuid = uuid.uuid4()
        workspace_exec_op = WorkspaceExecutedOperation.objects.create(
            id = workspace_exec_op_uuid,
            owner = self.regular_user_1,
            workspace= workspace,
            operation = op,
            job_id = workspace_exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )
        exec_op_uuid = uuid.uuid4()
        exec_op = ExecutedOperation.objects.create(
            id = exec_op_uuid,
            owner = self.regular_user_1,
            operation = op,
            job_id = exec_op_uuid, # does not have to be the same as the pk, but is here
            mode = 'foo'
        )

        ex_ops = ExecutedOperation.objects.all()
        workspace_ex_ops = WorkspaceExecutedOperation.objects.all()
        self.assertTrue(len(ex_ops) > 0)
        self.assertTrue(len(workspace_ex_ops) > 0)

        mock_obj = {
            'abc':123
        }
        mock_get_operation_instance_data.return_value = mock_obj

        finalize_executed_op(exec_op_uuid)
        mock_finalize_job.assert_called_with(exec_op, mock_obj)

        finalize_executed_op(workspace_exec_op_uuid)
        mock_finalize_job.assert_called_with(workspace_exec_op,  mock_obj)