import logging
import os
import json

from django.conf import settings

from celery.decorators import task

from api.models import Resource, ResourceMetadata, Operation, ExecutedOperation
from api.utilities import basic_utils
from api.utilities.ingest_operation import perform_operation_ingestion
import api.utilities.resource_utilities as resource_utilities
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer
from api.runners import submit_job

logger = logging.getLogger(__name__)

@task(name='delete_file')
def delete_file(path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    settings.RESOURCE_STORAGE_BACKEND.delete(path)

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

    # move the file backing this Resource.
    # Note that we do this BEFORE validating so that the validation functions don't
    # have to contain different steps for handling new uploads or requests to
    # change the type of a Resource.  By immediately moving the file to its 
    # final storage backend, we can handle all the variations in the same manner.
    try:
        resource.path = resource_utilities.move_resource_to_final_location(resource)
    except Exception as ex:
        logger.error('Caught an exception when moving the Resource {pk} to its'
            ' final location.  Exception was: {ex}'.format(
                pk = resource_pk,
                ex = ex
            )
        )
        resource.status = Resource.UNEXPECTED_STORAGE_ERROR
    else:    
        resource_utilities.validate_resource(resource, requested_resource_type)

    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True
    resource.save()

@task(name='ingest_new_operation')
def ingest_new_operation(operation_uuid_str, repository_url):
    '''
    This function kicks off the ingestion process for a new Operation
    '''
    perform_operation_ingestion(repository_url, operation_uuid_str)

@task(name='submit_job')
def submit_async_job(executed_op_pk, op_pk, validated_inputs):
    '''

    '''
    logger.info('Submitting an async job ({exec_op}).'.format(
        exec_op = str(executed_op_pk)
    ))
    try:
        executed_op = ExecutedOperation.objects.get(pk=executed_op_pk)
    except ExecutedOperation.DoesNotExist:
        logger.error('An async task received a primary key for an ExecutedOperation'
            ' that did not exist. PK={exec_op}'.format(
                exec_op = executed_op_pk
            )
        )
    try:
        op = Operation.objects.get(pk=op_pk)
    except Operation.DoesNotExist:
        logger.error('An async task received a primary key for an Operation'
            ' that did not exist. PK={op}'.format(
                op = op_pk
            )
        )
    submit_job(executed_op, op, validated_inputs)