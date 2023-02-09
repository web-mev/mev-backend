import logging

from celery import shared_task
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.conf import settings

from api.storage import S3_PREFIX
from api.utilities.globus import \
    create_user_transfer_client, \
    create_application_transfer_client
from api.models import GlobusTask
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)


@shared_task(name='poll_globus_task')
def poll_globus_task(task_id):
    try:
        task = GlobusTask.objects.get(task_id=task_id)
    except GlobusTask.DoesNotExist:
        logger.info(f'Could not locate task with ID: {task_id}') 
        alert_admins('Failed to poll a Globus transfer task.'
            f' Received an invalid ID of {task_id}'
        )

    user_transfer_client = create_user_transfer_client(task.user)

    logger.info(f'Query Globus for transfer status ({task_id})')
    while not user_transfer_client.task_wait(task_id):
        logger.info(f'Task {task_id} not complete.')

    logger.info(f'Task {task_id} completed.')
    for info in user_transfer_client.task_successful_transfers(task_id):
        # this is relative to the Globus bucket
        rel_path = info['destination_path']
        path = f'{S3_PREFIX}{settings.GLOBUS_BUCKET}/{rel_path}'
        # Note that even if Globus says the transfer is complete,
        # we can have a race condition where the copy does not work
        # since boto3 can't (yet) locate the source object. Thus,
        # we wait before attempting the copy
        default_storage.wait_until_exists(path)
        default_storage.create_resource_from_interbucket_copy(
            task.user,
            path
        )
    # Now that the transfer is complete, we can remove modify the ACL on
    # the collection and mark this transfer as complete (in our local db)
    app_transfer_client = create_application_transfer_client()
    logger.info(f'Remove endpoint rule {task.rule_id} for user {task.user}')
    result = app_transfer_client.delete_endpoint_acl_rule(
        settings.GLOBUS_ENDPOINT_ID, task.rule_id)
    logger.info(f'Rule removal result {result}')
    
    task.transfer_complete = True
    task.save()

