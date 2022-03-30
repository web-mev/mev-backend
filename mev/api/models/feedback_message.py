from django.db import models
from django.contrib.auth import get_user_model

class FeedbackMessage(models.Model):
    '''
    A simple model to hold user-submitted feedback
    '''

    message = models.CharField(
        max_length = 10000,
        null = False  
    )

    message_datetime = models.DateTimeField(
        auto_now_add = True
    )

    # the user who submitted the feedback
    user = models.ForeignKey(
        get_user_model(), 
        related_name = 'messages', 
        null = True,
        on_delete = models.SET_NULL
    )
