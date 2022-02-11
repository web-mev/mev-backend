import logging

from django.contrib.auth import get_user_model
#from celery.decorators import task
from celery import shared_task

from api.models import Operation, \
    ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Workspace
from api.utilities.ingest_operation import perform_operation_ingestion
from api.runners import submit_job, finalize_job
from api.utilities.operations import get_operation_instance_data

logger = logging.getLogger(__name__)

@shared_task(name='ingest_new_operation')
def ingest_new_operation(operation_uuid_str, repository_url):
    '''
    This function kicks off the ingestion process for a new Operation
    '''
    try:
        operation = Operation.objects.get(id=operation_uuid_str)
    except Operation.DoesNotExist:
        logger.error('Could not find the Operation corresponding to'
            ' id={u}'.format(u=op_uuid)
        )
        raise Exception('Encountered issue when trying update an Operation'
            ' database instance after ingesting from repository.'
        )     
    try:
        perform_operation_ingestion(repository_url, operation_uuid_str)
    except Exception:
        operation.successful_ingestion = False
        operation.save()

@shared_task(name='submit_async_job')
def submit_async_job(executed_op_pk, op_pk, user_pk, workspace_pk, job_name, validated_inputs):
    '''

    '''
    logger.info('Submitting an async job ({exec_op}).'.format(
        exec_op = str(executed_op_pk)
    ))

    # get the user:
    user = get_user_model().objects.get(pk=user_pk)

    # get the workspace instance if the pk was given:
    if workspace_pk is not None:
        logger.info('the workspace PK ({pk}) was given, so this is a workspace-associated job'.format(pk=workspace_pk))
        workspace_related_job = True
        workspace = Workspace.objects.get(id=workspace_pk)
    else:
        logger.info('No workspace PK given.')
        workspace_related_job = False

    try:
        op = Operation.objects.get(pk=op_pk)
        logger.info(op)
    except Operation.DoesNotExist:
        logger.error('An async task received a primary key for an Operation'
            ' that did not exist. PK={op}'.format(
                op = op_pk
            )
        )
        raise Exception('Unexpected exception when invoking an Operation-- could not'
            ' find the Operation'
        )

    # need to read the Operation definition to get the run mode:
    op_data = get_operation_instance_data(op)

    # Create an ExecutedOperation to track the job
    if workspace_related_job:
        logger.info('Create a WorkspaceExecutedOperation')
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = user,
            workspace=workspace,
            job_name = job_name,
            inputs = validated_inputs,
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.SUBMITTED
        )
    else:
        logger.info('Create a vanilla ExecutedOperation')
        executed_op = ExecutedOperation.objects.create(
            id=executed_op_pk,
            owner = user,
            job_name = job_name,
            inputs = validated_inputs,
            operation = op,
            mode = op_data['mode'],
            status = ExecutedOperation.SUBMITTED
        )
    submit_job(executed_op, op_data, validated_inputs)

@shared_task(name='finalize_executed_op')
def finalize_executed_op(exec_op_uuid):
    '''
    Performs some final operations following an analysis. Typically
    involves tasks like registering files to a user, etc.
    '''
    logger.info('Finalize executed op with ID={id}'.format(id=exec_op_uuid))

    # Depending on the execution context, we either have jobs that are workspace-
    # independent or those that are attached to a workspace. We therefore need
    # to get the specific type. We first query the most general kind (Which 
    # should always be successful), but we then attempt to query the more specific
    # WorkspaceExecutedOperation, which will fail if the operation was workspace-
    # independent.
    executed_op = ExecutedOperation.objects.get(pk=exec_op_uuid)
    try:
        executed_op = WorkspaceExecutedOperation.objects.get(pk=exec_op_uuid)
    except WorkspaceExecutedOperation.DoesNotExist:
        pass 
    finalize_job(executed_op)
