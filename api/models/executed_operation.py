import uuid

from django.db import models

from api.models import Operation

class ExecutedOperation(models.Model):
    '''
    An `ExecutedOperation` is an "executed" instance of a particular
    `Operation`.  The `Operation` describes what was done (i.e. which analysis)
    and the `ExecutedOperation` tracks information about the actual exection
    of that `Operation` type.   
    '''

    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4, 
        editable = False
    )

    # the reference to the type of Operation performed.
    operation = models.ForeignKey(
        Operation,
        on_delete = models.CASCADE
    )

    # When did the Operation start
    execution_start_datetime = models.DateTimeField(
        auto_now_add = True
    )

    # When did the Operation stop, even if unsuccessful
    execution_stop_datetime = models.DateTimeField()