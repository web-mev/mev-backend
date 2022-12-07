import unittest.mock as mock
import uuid

from exceptions import JobSubmissionException

from api.tests.base import BaseAPITestCase
from api.runners import submit_job


class RunnerFunctionsTester(BaseAPITestCase):

    @mock.patch('api.runners.get_runner')
    def test_runner_job_exception_raises(self,  mock_get_runner):
        '''
        If the call to the runner.run method experiences
        unexpected behavior and raises an exception, assert
        that we raise a JobSubmissionException
        '''
        mock_runner_cls = mock.MagicMock()
        mock_get_runner.return_value = mock_runner_cls

        mock_runner = mock.MagicMock()
        mock_runner.run.side_effect = Exception('!!!')
        mock_runner_cls.return_value = mock_runner

        mock_ex_op = mock.MagicMock()
        mock_pk = uuid.uuid4()
        mock_ex_op.pk = mock_pk
        mock_op = mock.MagicMock()

        with self.assertRaisesRegex(JobSubmissionException, 
                                    f'Failed to submit job {mock_pk}'):
            submit_job(mock_ex_op, mock_op, {})

        mock_runner.run.assert_called_with(mock_ex_op, mock_op, {})
