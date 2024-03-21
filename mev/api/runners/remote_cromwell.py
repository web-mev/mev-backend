import datetime

from api.runners.base import OperationRunner
from api.utilities.admin_utils import alert_admins
from api.models.executed_operation import ExecutedOperation


class RemoteCromwellRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using the WDL/Cromwell
    framework.

    NOTE: This class is kept to maintain backward compabitbility, but will
          NOT run jobs unless a Cromwell server has been set up.
    '''
    NAME = 'cromwell'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = OperationRunner.REQUIRED_FILES

    def run(self, executed_op, op, validated_inputs):
        alert_admins('A cromwell job run was attempted. This is an error.')
        executed_op.error_messages = ['The Cromwell-based job runner has been deprecated.'
            ' This job was submitted in error and an administrator has been notified']
        executed_op.execution_stop_datetime = datetime.datetime.now()
        executed_op.job_failed = True
        executed_op.status = ExecutedOperation.COMPLETION_ERROR
        executed_op.is_finalizing = False
        executed_op.save()