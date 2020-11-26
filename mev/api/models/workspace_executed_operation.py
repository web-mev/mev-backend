from django.db import models

from api.models import Workspace, ExecutedOperation

class WorkspaceExecutedOperation(ExecutedOperation):
    '''
    A `WorkspaceExecutedOperation` is a specialization of the 
    `ExecutedOperation` for operations that are created and run
    in the context of a user's `Workspace`
    '''

     # the workspace to which we associate this ExecutedOperation
    workspace = models.ForeignKey(
        Workspace,
        on_delete = models.CASCADE
    )