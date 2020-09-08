import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField

from api.models import Operation, Workspace

class ExecutedOperation(models.Model):
    '''
    An `ExecutedOperation` is an "executed" instance of a particular
    `Operation`.  The `Operation` describes what was done (i.e. which analysis)
    and the `ExecutedOperation` tracks information about the actual exection
    of that `Operation` type.   
    '''

    # Some status messages to display:
    SUBMITTED = 'Submitted.'
    QUEUED = 'Queued for execution.'
    RUNNING = 'Running.'
    COMPLETION_SUCCESS = 'Successfully completed.'
    COMPLETION_ERROR = 'An error occurred during execution.'
    ADMIN_NOTIFIED = 'An administrator has been notified.'

    # This tracks the unique run in our system
    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4, 
        editable = False
    )

    # the workspace to which we associate this ExecutedOperation
    workspace = models.ForeignKey(
        Workspace,
        on_delete = models.CASCADE
    )

    # the reference to the type of Operation performed.
    operation = models.ForeignKey(
        Operation,
        on_delete = models.CASCADE
    )

    # This helps us locate the job itself, so we can track progress.
    # For local Docker-based jobs, this would be the container ID. For
    # remote Cromwell-based jobs, this would be the Cromwell UUID.
    job_id = models.UUIDField(
        primary_key = False, 
        default = uuid.uuid4, 
        editable = True
    )

    # The inputs to this job-- a JSON document structured as an
    # api.data_structures.UserOperationInput instance
    inputs = JSONField(null=True)

    # The outputs of the job. Initially blank, but ultimately filled 
    # with the appropriate output in the form of an
    # api.data_structures.OperationOutput
    outputs = JSONField(null=True)

    # The job status-- for displaying updates/current status (e.g. "running").
    # Depends on which runner, etc.
    status = models.CharField(
        max_length = 255,
        default = ''
    )

    # When did the Operation start
    execution_start_datetime = models.DateTimeField(
        auto_now_add = True
    )

    # When did the Operation stop, even if unsuccessful
    execution_stop_datetime = models.DateTimeField(null=True)