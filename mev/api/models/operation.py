import uuid

from django.db import models
from django.utils import timezone


class Operation(models.Model):
    '''
    An `Operation` is any data manipulation or analysis step that can be performed.
    '''

    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4, 
        editable = False
    )
    active = models.BooleanField(default=False)
    name = models.CharField(max_length = 100)
    successful_ingestion = models.BooleanField(null=True)
    workspace_operation = models.BooleanField(default=False)
    addition_datetime = models.DateTimeField(
        default=timezone.now)
    git_commit = models.CharField(max_length=50, null=False)
    repository_url = models.URLField(max_length=500, null=False)