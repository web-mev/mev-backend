import logging

from celery import shared_task
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.conf import settings

from api.storage import S3_PREFIX
from api.utilities.globus import \
    create_application_transfer_client

logger = logging.getLogger(__name__)


@shared_task(name='poll_globus_task')
def poll_globus_task(task_id, user_pk):
    user = get_user_model().objects.get(pk=user_pk)
    client = create_application_transfer_client()
    logger.info(f'Query Globus for transfer status ({task_id})')
    while not client.task_wait(task_id):
        logger.info(f'Task {task_id} not complete.')

    logger.info(f'Task {task_id} completed.')  
    for info in client.task_successful_transfers(task_id):
        # this is relative to the Globus bucket
        rel_path = info['destination_path']
        path = f'{S3_PREFIX}{settings.GLOBUS_BUCKET}/{rel_path}'
        default_storage.create_resource_from_interbucket_copy(
            user,
            path
        )
