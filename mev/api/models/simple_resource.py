import uuid
import os

from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

def upload_to(instance, path):
    return os.path.join(str(instance.owner.pk), path)

class SimpleResource(models.Model):
    id = models.UUIDField(
        primary_key = True, 
        default = uuid.uuid4, 
        editable = False
    )
    name = models.CharField(max_length = 100)
    path = models.FileField(upload_to=upload_to)    
    owner = models.ForeignKey(
        get_user_model(), 
        related_name = 'simple_resources', 
        on_delete = models.CASCADE,
        blank = False,
        null = False
    )
