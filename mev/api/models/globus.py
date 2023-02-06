from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import JSONField


class GlobusTokens(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        related_name='globus_tokens',
        on_delete=models.CASCADE
    )
    tokens = JSONField()