import logging
import os
import json

from django.conf import settings

from celery.decorators import task

from api.models import Resource, ResourceMetadata
from api.utilities import basic_utils
import api.utilities.resource_utilities as resource_utilities
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer

logger = logging.getLogger(__name__)

@task(name='delete_file')
def delete_file(path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    settings.resource_storage_backend.delete(path)

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
    files.  Also handles validation when a "type change" is requested.

    Previous to calling this function, we set the `is_valid` flag
    to False so that the `Resource` is disabled for use.
    '''
    resource = resource_utilities.get_resource_by_pk(resource_pk)

    resource_utilities.validate_resource(resource, requested_resource_type)

    # now move the file backing this Resource
    resource_utilities.move_resource_to_final_location(resource)

    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True
    resource.save()