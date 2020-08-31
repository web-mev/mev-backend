import uuid

from django.db import models

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