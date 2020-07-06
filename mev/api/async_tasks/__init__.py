import logging
import os
import json

from django.conf import settings

from celery.decorators import task

from api.models import Resource, ResourceMetadata
from api.utilities import basic_utils
from api.utilities.resource_utilities import handle_valid_resource
from resource_types import get_resource_type_instance
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer

logger = logging.getLogger(__name__)

@task(name='delete_file')
def delete_file(path):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    resource_storage_backend = import_string(settings.RESOURCE_STORAGE_BACKEND)()
    resource_storage_backend.delete(path)


@task(name='validate_resource')
def validate_resource(resource_pk, requested_resource_type):
    '''
    This function handles the background validation of uploaded
    files.  Also handles validation when a "type change" is requested.

    Previous to calling this function, we set the `is_valid` flag
    to False so that the `Resource` is disabled for use.
    '''
    if requested_resource_type is not None:
        try:
            resource = Resource.objects.get(pk=resource_pk)
        except Resource.DoesNotExist as ex:
            logger.error('Received an unknown/invalid primary key'
            ' when trying to retrieve a Resource instance in an async'
            ' task.  PK was {uuid}.'.format(uuid=str(resource_pk))
        )
            raise ex

        # The resource type is the shorthand identifier.
        # This returns an actual resource class implementation
        resource_class_instance = get_resource_type_instance(requested_resource_type)

        # now validate the type
        is_valid, message = resource_class_instance.validate_type(resource.path)

        if is_valid:
            handle_valid_resource(resource, resource_class_instance, requested_resource_type)
        else:
            # again, if resource_type has not been set, then this   
            # Resource has NEVER been verified.  We report a failure
            # via the status message and set the appropriate flags

            if not resource.resource_type:
                resource.status = Resource.FAILED.format(
                    requested_resource_type=requested_resource_type
                )
            else:
                # if a resource_type was previously set, that means
                # it was previously valid and has now been changed to
                # an INvalid type.  In this case, revert back to the
                # valid type and provide a helpful status message
                # so they understand why the request did not succeed. 
                resource.status = Resource.REVERTED.format(
                    requested_resource_type=requested_resource_type,
                    original_resource_type = resource.resource_type
                )
    else: # requested_resource_type was None
        resource.resource_type = None
        
    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True
    resource.save()
