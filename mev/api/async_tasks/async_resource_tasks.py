import logging

from celery import shared_task

import api.utilities.resource_utilities as resource_utilities
from api.storage_backends import get_storage_backend
from api.models import Resource
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)

@shared_task(name='delete_file')
def delete_file(path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    get_storage_backend().delete(path)

@shared_task(name='store_resource')
def store_resource(resource_pk):
    resource = resource_utilities.get_resource_by_pk(resource_pk)
    resource_utilities.move_resource_to_final_location(resource)

@shared_task(name='validate_resource')
def validate_resource(resource_pk, requested_resource_type, file_format):
    '''
    This function only performs validation of the resource.
    
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)
    resource.status = Resource.VALIDATING
    resource.save()
    try:
        resource_utilities.initiate_resource_validation(resource, requested_resource_type, file_format)
    except Exception as ex:
        logger.info('Caught an exception raised during resource validation.')
        alert_admins(str(ex))
        resource.status = str(ex)
    resource.is_active = True
    resource.save()


@shared_task(name='validate_resource_and_store')
def validate_resource_and_store(resource_pk, requested_resource_type, file_format):
    '''
    This function handles the background validation of uploaded
    files.

    Previous to calling this function, we set the `is_active` flag
    to False so that the `Resource` is disabled for use.

    Note that the `resource_utilities.validate_and_store_resource`
    function performs a save on the passed Resource
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)
    resource.status = Resource.VALIDATING
    resource.save()
    try:
        resource_utilities.validate_and_store_resource(resource, requested_resource_type, file_format)
    except Exception as ex:
        logger.info('Caught an exception raised by the validate_and_store_resource function.')
        alert_admins(str(ex))
