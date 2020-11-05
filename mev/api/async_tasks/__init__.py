import logging
import os
import json

from celery.decorators import task

from api.models import Resource, \
    ResourceMetadata, \
    Operation, \
    ExecutedOperation, \
    Workspace
from api.utilities import basic_utils
from api.utilities.ingest_operation import perform_operation_ingestion
import api.utilities.resource_utilities as resource_utilities
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer
from api.runners import submit_job, finalize_job
from api.utilities.operations import get_operation_instance_data
from api.storage_backends import get_storage_backend

logger = logging.getLogger(__name__)

@task(name='delete_file')
def delete_file(path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    get_storage_backend().delete(path)

@task(name='validate_resource')
def validate_resource(resource_pk, requested_resource_type):
    '''
    This function only performs validation of the resource
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)

    resource_utilities.validate_resource(resource, requested_resource_type)
        
    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True
    resource.save()


@task(name='validate_resource_and_store')
def validate_resource_and_store(resource_pk, requested_resource_type):
    '''
    This function handles the background validation of uploaded
    files.

    Previous to calling this function, we set the `is_active` flag
    to False so that the `Resource` is disabled for use.
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)
    resource_utilities.validate_and_store_resource(resource, requested_resource_type)

@task(name='ingest_new_operation')
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

@task(name='submit_async_job')
def submit_async_job(executed_op_pk, op_pk, workspace_pk, job_name, validated_inputs):
    '''

    '''
    logger.info('Submitting an async job ({exec_op}).'.format(
        exec_op = str(executed_op_pk)
    ))

    # get the workspace instance:
    workspace = Workspace.objects.get(id=workspace_pk)

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
    executed_op = ExecutedOperation.objects.create(
        id=executed_op_pk,
        workspace=workspace,
        job_name = job_name,
        inputs = validated_inputs,
        operation = op,
        mode = op_data['mode'],
        status = ExecutedOperation.SUBMITTED
    )

    submit_job(executed_op, op_data, validated_inputs)

@task(name='finalize_executed_op')
def finalize_executed_op(exec_op_uuid):
    '''
    Performs some final operations following an analysis. Typically
    involves tasks like registering files to a user, etc.
    '''
    logger.info('Finalize executed op with ID={id}'.format(id=exec_op_uuid))
    executed_op = ExecutedOperation.objects.get(pk=exec_op_uuid)
    finalize_job(executed_op)
