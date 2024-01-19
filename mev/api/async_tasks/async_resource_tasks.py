import logging

from celery import shared_task

from django.core.files.storage import default_storage
from django.conf import settings

from exceptions import ResourceValidationException

import api.utilities.resource_utilities as resource_utilities
from api.models import Resource
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)


@shared_task(name='delete_file')
def delete_file(resource_path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info(f'Requesting deletion of resource at path {resource_path}')
    default_storage.delete(resource_path)


@shared_task(name='validate_resource')
def validate_resource(resource_pk, requested_resource_type, file_format):
    '''
    This function only performs validation of the resource.
    
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)
    logger.info(f'Starting the async resource validation for resource {resource.pk}'
        ' located at {resource.datafile.name}'
    )
    resource.status = Resource.VALIDATING
    resource.save()
    try:
        resource_utilities.initiate_resource_validation(resource, requested_resource_type, file_format)
    except ResourceValidationException as ex:
        logger.info('Resource failed validation')
        resource.status = str(ex)
    except Exception as ex:
        logger.info('Caught an exception raised during resource validation.')
        resource.status = Resource.UNEXPECTED_VALIDATION_ERROR
        # since this raised an unexpected error, we want to check what went wrong
        # so we copy the file. Otherwise the user can delete the file and we will not
        # be able to debug the issue.
        dest_obj = f'{settings.DEBUG_DIR}/{resource.pk}'
        default_storage.copy_to_storage(settings.MEDIA_ROOT,
                                        resource.datafile.name,
                                        dest_object=dest_obj)
        alert_admins('Caught a file validation exception.'
                     f' File is cached at {dest_obj}. User attempted to'
                     f' validate as {requested_resource_type} with format'
                     f' {file_format}.')
    resource.is_active = True
    resource.save()