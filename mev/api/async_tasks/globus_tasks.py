import logging
import uuid
import os

from celery import shared_task
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.conf import settings

from globus_sdk import TransferData

from api.storage import S3_PREFIX
from api.utilities.globus import \
    create_user_transfer_client, \
    create_application_transfer_client, \
    add_acl_rule, \
    get_globus_uuid, \
    submit_transfer, \
    post_upload, \
    delete_acl_rule, \
    GLOBUS_UPLOAD, \
    GLOBUS_DOWNLOAD
from api.models import GlobusTask, \
    Resource
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)


@shared_task(name='poll_globus_task')
def poll_globus_task(task_id, transfer_direction):
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
    if transfer_direction == GLOBUS_UPLOAD:
        post_upload(user_transfer_client, task_id, task.user)

    # Now that the transfer is complete, we can remove modify the ACL on
    # the collection and mark this transfer as complete (in our db)
    delete_acl_rule(task.rule_id)
    task.transfer_complete = True
    task.save()

    # cleanup the file(s) sitting in the tmp globus bucket.
    # They are either transferred to the user's collection or in our
    # webmev storage bucket
    # TODO: implement this!


@shared_task(name='perform_globus_download')
def perform_globus_download(resource_pk_set, user_pk, request_data):
    '''
    For Globus to perform a download (i.e. from WebMeV -> Globus),
    we need to first copy the files to a location that is readable
    by our Globus endpoint. This copy can be a significant bottleneck
    for a frontend request, so we move the majority of the transfer
    logic to this async function.
    '''
    webmev_user = get_user_model().objects.get(pk=user_pk)
    app_transfer_client = create_application_transfer_client()
    user_transfer_client = create_user_transfer_client(webmev_user)
    user_uuid = get_globus_uuid(webmev_user)

    label = request_data['label']
    destination_endpoint_id = request_data['endpoint_id']

    # This `path` gives the root of the destination
    dest_folder = request_data['path']

    # Depending on how the user selected the destination, we might get
    # `folder[0]`. If so, the final destination is the combination of `path`
    # and `folder[0]`
    if 'folder[0]' in request_data:
        dest_folder = os.path.join(dest_folder, request_data['folder[0]'])

    # a temporary 'outbox' where we will place the files we 
    # are transferring. This way Globus can see them. This 
    # path is relative to the folder where the Globus
    # collection is based.
    tmp_folder = f'tmp-{uuid.uuid4()}/'

    resource_list = Resource.objects.filter(pk__in=resource_pk_set)
    final_paths = []
    for r in resource_list:
        object_name = f'{tmp_folder}{r.name}'
        default_storage.copy_out_to_bucket(
            r, settings.GLOBUS_BUCKET, object_name
        )
        final_paths.append(object_name)

    # Create a 'read' rule and add it to the Globus shared collection
    # Note that for this, we need to 'root' the tmp folder
    rule_id = add_acl_rule(
        app_transfer_client, user_uuid, '/'+tmp_folder, 'r')

    # Given that we are transferring AWAY from our application,
    # the source is our Globus endpoint (the shared collection)
    source_endpoint_id = settings.GLOBUS_ENDPOINT_ID

    transfer_data = TransferData(
        transfer_client=user_transfer_client,
        source_endpoint=source_endpoint_id,
        destination_endpoint=destination_endpoint_id,
        label=label)

    for source_path in final_paths:
        destination_path = os.path.join(
            dest_folder, os.path.basename(source_path))
        logger.info(f'Globus download: {source_path} --> {destination_path}')
        transfer_data.add_item(
            source_path=source_path,
            destination_path=destination_path
        )

    user_transfer_client.endpoint_autoactivate(source_endpoint_id)
    user_transfer_client.endpoint_autoactivate(destination_endpoint_id)

    task_id = submit_transfer(user_transfer_client, transfer_data)
    if task_id:
        task_data = user_transfer_client.get_task(task_id)
        GlobusTask.objects.create(
            user=webmev_user,
            task_id=task_id,
            rule_id=rule_id,
            label=task_data['label']
        )
        poll_globus_task(task_id, GLOBUS_DOWNLOAD)
    else:
        GlobusTask.objects.create(
            user=webmev_user,
            task_id='',
            rule_id=rule_id,
            label='',
            submission_failure=True
        )