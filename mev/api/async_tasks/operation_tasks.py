import logging

from django.contrib.auth import get_user_model
from django.conf import settings
from celery import shared_task

from exceptions import JobSubmissionException

from api.models import Operation, \
    ExecutedOperation, \
    WorkspaceExecutedOperation, \
    Workspace
from api.utilities.ingest_operation import perform_operation_ingestion
from api.runners import submit_job, finalize_job, get_runner
from api.utilities.operations import get_operation_instance

logger = logging.getLogger(__name__)


@shared_task(name='ingest_new_operation')
def ingest_new_operation(operation_uuid_str, repository_url, commit_id):
    '''
    This function kicks off the ingestion process for a new Operation

    `repository_url` is the url to the git repo
    `commit_id` is the commit we want to ingest. Can be None, in which case we 
    will default to the main branch
    '''
    try:
        operation = Operation.objects.get(id=operation_uuid_str)
    except Operation.DoesNotExist:
        logger.error('Could not find the Operation corresponding to'
                     f' id={operation_uuid_str}')
        raise Exception('Encountered issue when trying update an Operation'
                        ' database instance after ingesting from repository.'
                        )
    try:
        perform_operation_ingestion(
            repository_url, operation_uuid_str, commit_id)
    except Exception:
        operation.successful_ingestion = False
        operation.save()


@shared_task(name='submit_async_job')
def submit_async_job(executed_op_pk, 
        op_pk, user_pk, workspace_pk, job_name, validated_inputs):
    '''

    '''
    logger.info('Submitting an async job ({exec_op}).'.format(
        exec_op=str(executed_op_pk)
    ))

    # get the user:
    user = get_user_model().objects.get(pk=user_pk)

    # get the workspace instance if the pk was given:
    if workspace_pk is not None:
        logger.info(f'the workspace PK ({workspace_pk}) was given, so this'
                    ' is a workspace-associated job.')
        workspace_related_job = True
        workspace = Workspace.objects.get(id=workspace_pk)
    else:
        logger.info('No workspace PK given.')
        workspace_related_job = False

    try:
        db_op = Operation.objects.get(pk=op_pk)
        logger.info(db_op)
    except Operation.DoesNotExist:
        logger.error('An async task received a primary key for an Operation'
                     f' that did not exist. PK={op_pk}')
        raise Exception('Unexpected exception when invoking an Operation-- could not'
                        ' find the Operation'
                        )

    # need to read the Operation definition to get the run mode:
    op = get_operation_instance(db_op)

    # Create an ExecutedOperation to track the job
    if workspace_related_job:
        logger.info('Create a WorkspaceExecutedOperation')
        executed_op = WorkspaceExecutedOperation.objects.create(
            id=executed_op_pk,
            owner=user,
            workspace=workspace,
            job_name=job_name,
            inputs=validated_inputs,
            operation=db_op,
            mode=op.mode,
            status=ExecutedOperation.SUBMITTED
        )
    else:
        logger.info('Create a vanilla ExecutedOperation')
        executed_op = ExecutedOperation.objects.create(
            id=executed_op_pk,
            owner=user,
            job_name=job_name,
            inputs=validated_inputs,
            operation=db_op,
            mode=op.mode,
            status=ExecutedOperation.SUBMITTED
        )

    try:
        submit_job(executed_op, op, validated_inputs)
    except JobSubmissionException as ex:
        logger.info('Caught a job submission exception.')
        return

    # also start a task that will watch for job status changes
    check_executed_op.delay(executed_op_pk)


@shared_task(name='check_executed_op', bind=True, max_retries=None)
def check_executed_op(task_self, exec_op_uuid):
    '''
    After jobs are submitted, this task tracks their status by 
    polling the job runner. In this way, we don't depend on API
    requests to initiate the job status checks.
    '''
    logger.info('Check on status of {id}'.format(id=exec_op_uuid))
    executed_op = ExecutedOperation.objects.get(pk=exec_op_uuid)
    runner_class = get_runner(executed_op.mode)
    runner = runner_class()
    try:
        has_completed = runner.check_status(executed_op.job_id)
    except Exception as ex:
        # Since it takes some time for the runner to start (e.g.
        # cromwell takes some time to parse inputs, etc.) the
        # call to check_status might return an error
        # do something here
        pass
    if has_completed:
        logger.info('Job ({id}) has completed. Kickoff'
                    ' finalization.'.format(
                        id=exec_op_uuid
                    )
                    )
        # kickoff the finalization. Set the flag for
        # blocking multiple attempts to finalize.
        executed_op.is_finalizing = True
        executed_op.status = ExecutedOperation.FINALIZING
        executed_op.save()
        finalize_executed_op.delay(exec_op_uuid)
    else:  # job still running
        task_self.retry(countdown=settings.JOB_STATUS_CHECK_INTERVAL)


@shared_task(name='finalize_executed_op')
def finalize_executed_op(exec_op_uuid):
    '''
    Performs some final operations following an analysis. Typically
    involves tasks like registering files to a user, etc.
    '''
    logger.info('Finalize executed op with ID={id}'.format(id=exec_op_uuid))

    # Depending on the execution context, we either have 
    # jobs that are workspace-independent or those that are attached 
    # to a workspace. We therefore need to get the specific type. 
    # We first query the most general kind (Which should always be successful),
    # but we then attempt to query the more specific 
    # WorkspaceExecutedOperation, which will fail if the 
    # operation was workspace-independent.
    executed_op = ExecutedOperation.objects.get(pk=exec_op_uuid)
    try:
        executed_op = WorkspaceExecutedOperation.objects.get(pk=exec_op_uuid)
    except WorkspaceExecutedOperation.DoesNotExist:
        pass

    op = get_operation_instance(executed_op.operation)
    finalize_job(executed_op, op)
