import logging

from celery.decorators import task

from api.models import Resource
from api.utilities.resource_utilities import move_resource_to_final_location
from api.resource_types import RESOURCE_MAPPING, resource_type_is_valid

logger = logging.getLogger(__name__)

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
    # To get the actual resource class implementation, we 
    # use the RESOURCE_MAPPING dict
    try:
        resource_class = RESOURCE_MAPPING[requested_resource_type]
    except KeyError as ex:
        logger.error('Received an unknown resource_type identifier:'
            ' {requested_resource_type}.  Current types are:'
            ' {resource_mapping}'.format(
                resource_mapping = RESOURCE_MAPPING,
                requested_resource_type = requested_resource_type
            )
        )
        raise ex 

    # check the validity
    is_valid, message = resource_type_is_valid(
        resource_class,
        resource.path
    )

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

        # this is here so that we can check if the resource_type
        # was previously null/None
        resource.resource_type = requested_resource_type

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
