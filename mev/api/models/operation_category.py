import uuid

from django.db import models

from api.models import Operation

class OperationCategory(models.Model):
    '''
    An `OperationCategory` allows us to logically group `Operation`s.
    '''
    operation = models.ForeignKey(
        Operation,
        on_delete = models.CASCADE
    )
    category = models.CharField(max_length = 100)
