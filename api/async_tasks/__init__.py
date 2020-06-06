import logging
import os
import json

from celery.decorators import task

from api.models import Resource, ResourceMetadata
from api.utilities import basic_utils
from api.utilities.resource_utilities import move_resource_to_final_location
from api.resource_types import get_resource_type_instance
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer

logger = logging.getLogger(__name__)

@task(name='delete_file')
def delete_file(path, is_local = True):
    '''
    Deletes a file.  Can be a local or remote resource.
    '''
    logger.info('Requesting deletion of {path}'.format(path=path))
    if is_local:
        basic_utils.copy_local_resource(path)
    else:
        raise NotImplementedError('Remote file removal not implemented.')

@task(name='validate_resource')
def validate_resource(resource_pk, requested_resource_type):
    '''
    This function handles the background validation of uploaded
    files.  Also handles validation when a "type change" is requested.

    Previous to calling this function, we set the `is_valid` flag
    to False so that the `Resource` is disabled for use.
    '''

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

        resource.status = Resource.READY

        # if the existing resource.resource_type field was not set (null/None)
        # then that means it has never passed validation (e.g. a new file).
        # Move it to its final location
        if not resource.resource_type:
            try:
                final_path = move_resource_to_final_location(resource)
                resource.path = final_path
            except Exception as ex:
                # a variety of exceptions can be raised due to failure
                # to create directories/files.  Catch them all here and
                # set the resource to be inactive.
                logger.error('An exception was raised following'
                ' successful validation of reosurce {resource}.'
                ' Exception trace is {ex}'.format(
                    ex=ex,
                    resource = resource
                ))

        resource.resource_type = requested_resource_type

        # since the resource was valid, we can also fill-in the metadata
        metadata = resource_class_instance.extract_metadata(resource.path)
        
        # need to check if there was already metadata for this Resource:
        rm = ResourceMetadata.objects.filter(resource=resource)
        if len(rm) > 1:
            logger.error('Database corruption-- multiple ResourceMetadata'
                ' instances associated with Resource: {resource}'.format(
                    resource=resource
                )
            )
        elif len(rm) == 0:
            rm = ResourceMetadata.objects.create(
                resource=resource,
                parent_operation=metadata['parent_operation'],
                observation_set=json.dumps(metadata['observation_set']),
                feature_set=json.dumps(metadata['feature_set']),
            )
        else: # had existing ResourceMetadata-- update
            rm = rm[0]
            rm.parent_operation=metadata['parent_operation']
            rm.observation_set=json.dumps(metadata['observation_set'])
            rm.feature_set=json.dumps(metadata['feature_set'])
            rm.save()


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
        
    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True
    resource.save()
