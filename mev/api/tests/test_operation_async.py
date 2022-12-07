import unittest.mock as mock
import uuid

from django.core.exceptions import ImproperlyConfigured

from exceptions import JobSubmissionException

from api.tests.base import BaseAPITestCase
from api.models import ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Operation, \
    Workspace
from api.async_tasks.operation_tasks import finalize_executed_op, \
    submit_async_job


class OperationAsyncTester(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

    @mock.patch('api.async_tasks.operation_tasks.finalize_job')
    @mock.patch('api.async_tasks.operation_tasks.get_operation_instance')
    def test_gets_correct_op_type(self,
                                  mock_get_operation_instance,
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
            id=workspace_exec_op_uuid,
            owner=self.regular_user_1,
            workspace=workspace,
            operation=op,
            # does not have to be the same as the pk, but is here
            job_id=workspace_exec_op_uuid,
            mode='foo'
        )
        exec_op_uuid = uuid.uuid4()
        exec_op = ExecutedOperation.objects.create(
            id=exec_op_uuid,
            owner=self.regular_user_1,
            operation=op,
            job_id=exec_op_uuid,  # does not have to be the same as the pk, but is here
            mode='foo'
        )

        ex_ops = ExecutedOperation.objects.all()
        workspace_ex_ops = WorkspaceExecutedOperation.objects.all()
        self.assertTrue(len(ex_ops) > 0)
        self.assertTrue(len(workspace_ex_ops) > 0)

        mock_op = mock.MagicMock()
        mock_get_operation_instance.return_value = mock_op

        finalize_executed_op(exec_op_uuid)
        mock_finalize_job.assert_called_with(exec_op, mock_op)

        finalize_executed_op(workspace_exec_op_uuid)
        mock_finalize_job.assert_called_with(workspace_exec_op, mock_op)

    @mock.patch('api.async_tasks.operation_tasks.alert_admins')
    @mock.patch('api.async_tasks.operation_tasks.check_executed_op')
    @mock.patch('api.async_tasks.operation_tasks.get_operation_instance')
    @mock.patch('api.async_tasks.operation_tasks.submit_job')
    def test_job_submission_errors_handled(self, mock_submit_job,
                                           mock_get_operation_instance,
                                           mock_check_executed_op,
                                           mock_alert_admins):
        '''
        Tests that we appropriately catch unexpected issues with job submission.

        The reason for this test was that an improperly specified operation spec
        (for an Operation) had a bad converter. When the inputs were being converted
        using the appropriate converter for the local Docker runner, an exception
        was raised. This was not caught and the job was never submitted (i.e.
        the Docker container was never executed). However, the job also got stuck
        in a limbo state and did not inform the user.
        '''

        # we mock out the response from the get_operation_instance function, but
        # we need to give an object that has the attributes necessary to run the test
        mock_op = mock.MagicMock()
        mock_op.mode = 'foo'
        mock_get_operation_instance.return_value = mock_op

        mock_submit_job.side_effect = JobSubmissionException('!!!')

        # setup the necessary elements for this test:
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

        executed_op_uuid = uuid.uuid4()
        submit_async_job(
            executed_op_uuid, op.pk, self.regular_user_1.pk, workspace.pk, 'job_name', {})

        mock_alert_admins.assert_called()
        ex_op = ExecutedOperation.objects.get(pk=executed_op_uuid)
        self.assertTrue(ex_op.job_failed)
        mock_check_executed_op.assert_not_called()