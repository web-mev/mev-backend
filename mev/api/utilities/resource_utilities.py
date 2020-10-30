import os
import uuid
import json
import logging

from django.utils.module_loading import import_string

from api.models import Resource, ResourceMetadata
from api.serializers.resource_metadata import ResourceMetadataSerializer
from .basic_utils import make_local_directory, \
    move_resource, \
    copy_local_resource
from api.storage_backends import get_storage_backend
from resource_types import get_contents, \
    get_resource_paginator as _get_resource_paginator, \
    extension_is_consistent_with_type, \
    get_acceptable_extensions, \
    DB_RESOURCE_STRING_TO_HUMAN_READABLE, \
    get_resource_type_instance, \
    PARENT_OP_KEY, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY

logger = logging.getLogger(__name__)

def get_resource_by_pk(resource_pk):
    try:
        resource = Resource.objects.get(pk=resource_pk)
        return resource
    except Resource.DoesNotExist as ex:
        logger.info('Received an unknown/invalid primary key'
        ' when trying to retrieve a Resource instance.'
        ' PK was {uuid}.'.format(uuid=str(resource_pk))
    )
        raise ex

def check_for_resource_operations(resource_instance):
    '''
    To prevent deleting critical resources, we check to see if a
    `Resource` instance has been used for any operations within a
    `Workspace`.  If it has, return True.  Otherwise return False.
    '''
    # TODO: implement once Operations have been added.
    # For the moment, False 
    return False


def set_resource_to_inactive(resource_instance):
    '''
    Function created to temporarily "disable"
    a Resource while it is pending verification of the
    type or uploading.  
    '''
    resource_instance.is_active = False
    resource_instance.save()


def copy_resource_to_workspace(unattached_resource, workspace):
    '''
    This function handles the copy of an existing (and validated)
    Resource when it is added to a Workspace.

    Note that it only creates the appropriate
    database object- in the case of large files, we
    do not want to copy those.
    '''
    logger.info('Adding resource ({resource}) to'
        ' workspace ({workspace}).'.format(
            workspace = str(workspace),
            resource = str(unattached_resource)
        )
    )  

    metadata_queryset = ResourceMetadata.objects.filter(resource=unattached_resource)

    # we need to create a new Resource with the Workspace 
    # field filled appropriately.  Note that this method of "resetting"
    # the primary key by setting it to None creates an effective copy
    # of the original resource. We then alter the path field and save.
    r = unattached_resource
    r.pk = None
    r.workspace = workspace
    r.is_public = False # when we copy to a workspace, set private
    r.save()

    # also need to copy the metadata
    if len(metadata_queryset) == 0:
        logger.error('Was trying to add Resource {r_uuid}'
            ' to a Workspace ({w_uuid}), but there was no'
            ' metadata associated with it'.format(
                r_uuid = unattached_resource.pk,
                w_uuid = workspace.pk
            ))
    elif len(metadata_queryset) > 1:
        logger.error('Was trying to add Resource {r_uuid}'
            ' to a Workspace ({w_uuid}), but there were'
            ' multiple metadata instances associated with it'.format(
                r_uuid = unattached_resource.pk,
                w_uuid = workspace.pk
            ))
    else:
        metadata = metadata_queryset[0]
        metadata.pk = None
        metadata.resource = r
        metadata.save()

    return r

def check_for_shared_resource_file(resource_instance):
    '''
    When a Resource deletion is requested, we need to be a bit careful about
    deleting database records, the underlying files, or both.

    Now we need to check if any OTHER Resource instances 
    reference the same path.  If there are, we only delete
    the database record, NOT the file.  If this is the only
    database record referring to the file, we can delete both
    the record and the file.

    Returns True if multiple Resources reference the same file.
    '''
    path = resource_instance.path
    if len(path) > 0: # in case the path was empty somehow.
        all_resources_with_path = Resource.objects.filter(path=path)
        if len(all_resources_with_path) == 0:
            logger.error('Unexpected exception when'
            ' attempting to delete a Resource instance. Despite'
            ' filtering with the path member, could not locate'
            ' any Resource instances referencing that same path.')
            raise Exception('No Resource found')

        elif len(all_resources_with_path) == 1: 
            # only one Resource record references the path.  
            # Double-check that it's the same as the current
            # instance we're considering 
            r = all_resources_with_path[0]
            if r.pk != resource_instance.pk:
                logger.error('Unexpected exception when'
                ' attempting to delete a Resource instance.  Did not "re-find"'
                ' the Resource instance we used to search with.')
                raise Exception('Database inconsistency!')
            else:
                # consistency check worked.  Only a singe Resource instance
                # references the file.  Delete both the file AND the record.
                return False
        else:
            return True
    else:
        logger.error('The path attribute of the Resource ({pk})'
            ' was empty.  This should not happen.'.format(
                pk=str(resource_instance.pk)
            )
        )
        raise Exception('Path was empty. Error.')


def get_resource_view(resource_instance, query_params={}):
    '''
    Returns a "view" of the resource_instance in JSON-format.

    Only valid for certain resource types and assumes
    that the resource is active. 
    '''
    logger.info('Retrieving data view for resource: {resource}.'.format(
        resource=resource_instance
    ))

    if not resource_instance.resource_type:
        logger.error('No resource type was known for resource: {resource}.'.format(
            resource = resource_instance
        ))
        return
    local_path = get_storage_backend().get_local_resource_path(resource_instance)
    return get_contents(local_path, resource_instance.resource_type, query_params)

def get_resource_paginator(resource_type):
    '''
    Depending on how a data resource is represented in the backend,
    it is possible we want to have multiple "paginator" classes which
    dictate how records are returned. This calls down to the
    class implementations for the resource_type and uses the logic there
    '''
    return _get_resource_paginator(resource_type)
    

def add_metadata_to_resource(resource, metadata):
    metadata[RESOURCE_KEY] = resource.pk
    try:
        rm = ResourceMetadata.objects.get(resource=resource)
        rms = ResourceMetadataSerializer(rm, data=metadata)
    except ResourceMetadata.DoesNotExist:
        rms = ResourceMetadataSerializer(data=metadata)
    if rms.is_valid(raise_exception=True):
        rms.save()

def move_resource_to_final_location(resource_instance):
    '''
    resource_instance is the database object
    '''
    return get_storage_backend().store(resource_instance)

def get_resource_size(resource_instance):
    return get_storage_backend().get_filesize(resource_instance.path)

def handle_valid_resource(resource, resource_class_instance, requested_resource_type):
    '''
    Once a Resource has been successfully validated, this function does some
    final operations such as moving the file and extracting metadata.

    `resource` is the database object
    `resource_class_instance` is one of the DataResource subclasses
    '''
    # Actions below require local access to the file:
    local_path = get_storage_backend().get_local_resource_path(resource)
    logger.info('The local path prior to standardization is: {p}'.format(p=local_path))

    # the resource was valid, so first save it in our standardized format
    new_path, new_name = resource_class_instance.save_in_standardized_format(local_path, resource.name)

    # delete the "original" resource, if the standardization ended up making
    # a different file

    if new_path != local_path:
        logger.info('The standardization changed the path. '
            'Go delete the non-standardized file: {p}'.format(p=resource.path)
        )
        get_storage_backend().delete(resource.path)

        # temporarily change this so it doesn't point at the original path
        # in the non-standardized format. This way the standardized file will be 
        # sent to the final storage location. Once the file is in the 'final' 
        # storage location, the path member will be edited to reflect that
        resource.path = new_path

    if new_name != resource.name:
        # change the name of the resource
        resource.name = new_name

    # since the resource was valid, we can also fill-in the metadata
    metadata = resource_class_instance.extract_metadata(new_path)
    add_metadata_to_resource(resource, metadata)

    # have to send the file to the final storage. If we are using local storage
    # this is trivial. However, if we are using remote storage, the data saved
    # in the standardized format needs to be pushed there also.
    final_path = move_resource_to_final_location(resource)

    resource.path = final_path
    resource.resource_type = requested_resource_type
    resource.status = Resource.READY


def check_extension(resource, requested_resource_type):
    '''
    Checks that the file extension is consistent with the requested
    resource type. Uses another function to check the extension, 
    and this function sets the necessary members on the resource
    instance if there is a problem.
    '''
    consistent_extension = extension_is_consistent_with_type(resource.name, requested_resource_type)
    if not consistent_extension:
        acceptable_extensions = ','.join(get_acceptable_extensions(requested_resource_type))
        resource.status = Resource.UNKNOWN_EXTENSION_ERROR.format(
            readable_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[requested_resource_type],
            filename = resource.name,
            extensions_csv = acceptable_extensions
        )
        return False
    return True


def handle_invalid_resource(resource_instance, requested_resource_type):

    # If resource_type has not been set (i.e. it is None), then this   
    # Resource has NEVER been verified.  We report a failure
    # via the status message and set the appropriate flags
    if not resource_instance.resource_type:
        resource_instance.status = Resource.FAILED.format(
            requested_resource_type=requested_resource_type
        )
    else:
        # if a resource_type was previously set, that means
        # it was previously valid and has now been changed to
        # an INvalid type.  In this case, revert back to the
        # valid type and provide a helpful status message
        # so they understand why the request did not succeed.
        # Obviously, we don't alter the resource_type member in this case.

        # get the "human-readable" types:
        hr_requested_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[
            requested_resource_type]
        hr_original_resource_type = DB_RESOURCE_STRING_TO_HUMAN_READABLE[
            resource_instance.resource_type]

        # ...and compose the status message
        resource_instance.status = Resource.REVERTED.format(
            requested_resource_type= hr_requested_resource_type,
            original_resource_type = hr_original_resource_type
        )
    
def validate_resource(resource_instance, requested_resource_type):
    '''
    This function performs validation against the requested resource
    type.  If that fails, reverts to the original type (or remains None
    if the resource has never been successfully validated).
    '''
    if requested_resource_type is not None:

        # check the file extension is consistent with the requested type:
        type_is_consistent = check_extension(resource_instance, requested_resource_type)
        if not type_is_consistent:
            return

        # The resource type is the shorthand identifier.
        # This returns an actual resource class implementation
        resource_class_instance = get_resource_type_instance(requested_resource_type)

        # Regardless of whether we are validating a new upload or changing the type
        # of an existing file, the file is already located at its "final" location
        # which is dependent on the storage backend.  Now, if the storage backend
        # is remote (e.g. bucket storage), we need to pull the file locally to 
        # perform validation.
        local_path = get_storage_backend().get_local_resource_path(resource_instance)
        try:
            is_valid, message = resource_class_instance.validate_type(local_path)
        except Exception as ex:
            logger.error('An exception was raised when attempting to validate'
                ' the Resource {pk} located at {local_path}'.format(
                    pk = str(resource_instance.pk),
                    local_path = local_path
                )
            )
            resource_instance.status = Resource.UNEXPECTED_VALIDATION_ERROR
            return

        if is_valid:
            handle_valid_resource(resource_instance, resource_class_instance, requested_resource_type)
        else:
            handle_invalid_resource(resource_instance, requested_resource_type)

    else: # requested_resource_type was None
        resource_instance.resource_type = None
        resource_instance.status = Resource.READY

def validate_and_store_resource(resource, requested_resource_type):

    # move the file backing this Resource.
    # Note that we do this BEFORE validating so that the validation functions don't
    # have to contain different steps for handling new uploads or requests to
    # change the type of a Resource.  By immediately moving the file to its 
    # final storage backend, we can handle all the variations in the same manner.
    try:
        resource.path = move_resource_to_final_location(resource)
    except Exception as ex:
        logger.error('Caught an exception when moving the Resource {pk} to its'
            ' final location.  Exception was: {ex}'.format(
                pk = str(resource.pk),
                ex = ex
            )
        )
        resource.status = Resource.UNEXPECTED_STORAGE_ERROR
    else:    
        validate_resource(resource, requested_resource_type)

    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True

    # save the filesize as well
    resource.size = get_resource_size(resource)
    resource.save()
