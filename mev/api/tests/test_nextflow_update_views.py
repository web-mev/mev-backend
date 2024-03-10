import uuid
import unittest.mock as mock

from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status

from api.models import Operation as OperationDbModel
from api.models import WorkspaceExecutedOperation, \
    Workspace
from api.tests.base import BaseAPITestCase
from api.runners.nextflow import NextflowRunner
from api.utilities.nextflow_utils import NEXTFLOW_PROCESS_STARTED, \
    NEXTFLOW_COMPLETED, \
    NEXTFLOW_ERROR


class NextflowStatusUpdateTests(BaseAPITestCase):

    def setUp(self):

        self.url = reverse('nextflow-status-update')
        self.establish_clients()

        op_uuid = uuid.uuid4()
        op = OperationDbModel.objects.create(id=str(op_uuid))        
        # need a user's workspace to create an ExecutedOperation
        user_workspaces = Workspace.objects.filter(owner=self.regular_user_1)
        if len(user_workspaces) == 0:
            msg = '''
                Testing not setup correctly.  Please ensure that there is at least one
                Workspace for user {user}.
            '''.format(user=self.regular_user_1)
            raise ImproperlyConfigured(msg)
        workspace = user_workspaces[0]
        self.exec_op_uuid = uuid.uuid4()
        self.job_id = f'{NextflowRunner.JOB_PREFIX}{self.exec_op_uuid}'
        self.exec_op = WorkspaceExecutedOperation.objects.create(
            id=self.exec_op_uuid,
            owner=self.regular_user_1,
            workspace= workspace,
            operation=op,
            job_id=self.job_id,
            mode='foo'
        )

    def test_view_does_not_require_auth(self):
        """
        Test that this view does not require an auth token.
        The view is protected from external traffic by proxy config
        """
        data = {
            'event': 'something',
            'runName': 'some_run'
        }
        response = self.regular_client.post(self.url, data=data, format='json')
        self.assertTrue(response.status_code == status.HTTP_200_OK)

    @mock.patch('api.views.nextflow_views.write_final_nextflow_metadata')
    def test_running_job_sets_status(self, mock_write_final_nextflow_metadata):
        """
        Test that we update the `status` field on the database model
        when the job is still running, but do NOT execute downstream 
        tasks
        """
        data = {
            'event': NEXTFLOW_PROCESS_STARTED, # not yet complete
            'runName': self.job_id    
        }
        response = self.regular_client.post(self.url, data=data, format='json')
        self.assertTrue(response.status_code == status.HTTP_200_OK)
        mock_write_final_nextflow_metadata.assert_not_called()

    @mock.patch('api.views.nextflow_views.write_final_nextflow_metadata')
    def test_completed_job_sets_status(self, mock_write_final_nextflow_metadata):
        """
        Test that we update the `status` field on the database model
        when the job has completed and execute downstream 
        tasks
        """
        data = {
            'event': NEXTFLOW_COMPLETED,
            'runName': self.job_id    
        }
        response = self.regular_client.post(self.url, data=data, format='json')
        self.assertTrue(response.status_code == status.HTTP_200_OK)
        mock_write_final_nextflow_metadata.assert_called_with(data, self.exec_op_uuid)
        # re-query op to ensure it was saved:
        updated_exec_op = WorkspaceExecutedOperation.objects.get(pk=self.exec_op_uuid)
        self.assertTrue(updated_exec_op.status == NEXTFLOW_COMPLETED)

    @mock.patch('api.views.nextflow_views.alert_admins')
    def test_missing_job_notifies_admins(self, mock_alert_admins):
        """
        For the instance where the view receives a payload which does
        not match a known executed operation, ensure that we notify
        the admins. Not clear how this error could be generated, but
        we catch it nonetheless
        """
        data = {
            'event': NEXTFLOW_COMPLETED,
            'runName': 'some_bad_id'    
        }
        response = self.regular_client.post(self.url, data=data, format='json')
        # the response is 200 no matter what since the nextflow-generated POST
        # request would only generate a log if it was NOT 200
        mock_alert_admins.assert_called()

    @mock.patch('api.views.nextflow_views.alert_admins')
    def test_job_failure_notifies_admins(self, mock_alert_admins):
        """
        If the job fails, we get a NEXTFLOW_ERROR sent as the 'event'.
        Assert that we notify the admins. Typically this error is generated
        if the nextflow file has bad syntax , etc. so not something that
        should be generated a lot for mature/correct jobs
        """
        data = {
            'event': NEXTFLOW_ERROR,
            'runName': 'some_id'    
        }
        response = self.regular_client.post(self.url, data=data, format='json')
        # the response is 200 no matter what since the nextflow-generated POST
        # request would only generate a log if it was NOT 200
        mock_alert_admins.assert_called()