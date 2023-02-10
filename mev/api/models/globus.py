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


class GlobusTask(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        related_name='globus_tasks',
        on_delete=models.CASCADE
    )
    # the task ID is the unique ID for the transfer
    task_id = models.CharField(max_length=50, primary_key=True)

    # For each transfer, we add a rule to allow the user to write
    # to a specific location in our Globus bucket. We eventually want
    # to remove that once the transfer is complete. Store that here.
    rule_id = models.CharField(max_length=50, null=False, blank=False)

    # save the user-assigned transfer label so they can identify it more easily
    label = models.CharField(max_length=100, blank=True, default='')

    # whether the transfer is complete or not. This allows us to locally
    # track ongoing and completed transfers
    transfer_complete = models.BooleanField(default=False)
