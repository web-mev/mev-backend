import os
import uuid
import json
import logging

from django.utils.module_loading import import_string
from django.db.utils import OperationalError
from rest_framework.exceptions import ValidationError

from api.models import Resource, ResourceMetadata, ExecutedOperation
from api.exceptions import AttributeValueError
from api.serializers.resource_metadata import ResourceMetadataSerializer
from .basic_utils import make_local_directory, \
    move_resource, \
    copy_local_resource
from api.data_structures.attributes import DataResourceAttribute
from api.storage_backends import get_storage_backend
from resource_types import get_contents, \
    get_resource_paginator as _get_resource_paginator, \
    extension_is_consistent_with_type, \
    resource_supports_pagination as _resource_supports_pagination, \
    get_acceptable_extensions, \
    DB_RESOURCE_STRING_TO_HUMAN_READABLE, \
    get_resource_type_instance, \
    PARENT_OP_KEY, \
    OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY, \
    RESOURCE_KEY, \
    RESOURCE_TYPES_WITHOUT_CONTENTS_VIEW, \
    RESOURCE_MAPPING

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

def set_resource_to_inactive(resource_instance):
    '''
    Function created to temporarily "disable"
    a Resource while it is pending verification of the
    type or uploading.  
    '''
    resource_instance.is_active = False
    resource_instance.save()


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
        logger.info('No resource type was known for resource: {resource}.'.format(
            resource = resource_instance
        ))
        return
    if RESOURCE_MAPPING[resource_instance.resource_type] in RESOURCE_TYPES_WITHOUT_CONTENTS_VIEW:
        # prevents us from pulling remote resources if we can't view the contents anyway
        return None
    else:
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
    d = {}
    d[RESOURCE_KEY] = resource.pk
    metadata.update(d)
    try:
        rm = ResourceMetadata.objects.get(resource=resource)
        rms = ResourceMetadataSerializer(rm, data=metadata)
    except ResourceMetadata.DoesNotExist:
        rms = ResourceMetadataSerializer(data=metadata)
    if rms.is_valid(raise_exception=True):
        try:
            rms.save()
        except OperationalError as ex:
            logger.error('Failed when adding ResourceMetadata.'
                ' Reason was: {ex}'.format(
                    ex=ex
                )
            )
            # if the save failed (e.g. perhaps b/c it was too large)
            # then just fill in blank metadata.
            rms = ResourceMetadataSerializer(data=d)
            rms.save()
        except Exception as ex:
            logger.error('Caught an unexpected error when trying to save metadata'
                ' for resource with pk={pk}'.format(pk=resource.pk)
            )            
            rms = ResourceMetadataSerializer(data=d)
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
    # if the resource class is capable of performing validation, we enter here.
    # This does NOT mean that any of the standardization, etc. steps occur, but
    # this admits that possibility.
    # If the resource type is such that is does not support validation, then we 
    # skip this part as we have no need to pull the file locally (if the storage
    # backend is remote)
    if resource_class_instance.performs_validation():

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
        else:
            logger.info('Standardization did not change the path...')

        if new_name != resource.name:
            # change the name of the resource
            resource.name = new_name
    else:
        # since we did not have to perform any standardization, etc. simply
        # set the necessary variables without change.
        new_path = resource.path
        new_name = resource.name

    # since the resource was valid, we can also fill-in the metadata
    # Note that the metadata could fail for type issues and we have to plan
    # for failures there. For instance, a table can be compliant, but the 
    # resulting metadata could violate a type constraint (e.g. if a string-based
    # attribute does not match our regex)
    try:
        metadata = resource_class_instance.extract_metadata(new_path)
    except ValidationError as ex:
        logger.info('Caught a ValidationError when extracting metadata from'
            ' resource at path: {p}'.format(p=new_path)
        )
        err_list = []
        for k,v in ex.get_full_details().items():
            # v is a nested dict
            msg = v['message']
            err_str = '{k}:{s}'.format(k=k, s = str(msg))
            err_list.append(err_str)
        resource.status = Resource.ERROR_WITH_REASON.format(ex=','.join(err_list))
        resource.resource_type = None
        return
    except Exception as ex:
        logger.info('Encountered an exception when extracting metadata: {ex}'.format(
            ex = ex
        ))
        resource.status = Resource.ERROR_WITH_REASON.format(ex=ex)
        resource.resource_type = None
        return

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
        # add empty metadata so that other methods which may try to access
        # that metadata do not break.
        add_metadata_to_resource(resource_instance, {})

    else:
        # if a resource_type was previously set, that means
        # it was previously valid and has now been changed to
        # an INvalid type.  In this case, revert back to the
        # valid type and provide a helpful status message
        # so they understand why the request did not succeed.
        # Obviously, we don't alter the resource_type member in this case.

        # Also, note that we do NOT edit metadata here, as we do not
        # want to ruin the existing metadata since we are reverting to the 
        # previously valid type.

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
        try:
            type_is_consistent = check_extension(resource_instance, requested_resource_type)
        except Exception as ex:
            resource_instance.status = Resource.ERROR_WITH_REASON.format(ex=ex)
            return

        if not type_is_consistent:
            logger.info('The requested type was not consistent with the file extension. Skipping validation.')
            resource_instance.status = Resource.ERROR_WITH_REASON.format(ex='Requested resource type'
                ' was not consistent with the file extension'
            )
            return

        # The resource type is the shorthand identifier.
        # This returns an actual resource class implementation
        try:
            resource_class_instance = get_resource_type_instance(requested_resource_type)
        except KeyError as ex:
            resource_instance.status = Resource.ERROR_WITH_REASON.format(ex=ex)
            return

        if resource_class_instance.performs_validation():

            logger.info('Since the resource class permits validation, go and'
                ' validate this resource.')

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
        else: # resource type does not include validation
            is_valid = True

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
        try:
            validate_resource(resource, requested_resource_type)
        except Exception as ex:
            resource.status = Resource.ERROR_WITH_REASON.format(ex=ex)

    # regardless of what happened above, set the 
    # status to be active (so changes can be made)
    # and save the instance
    resource.is_active = True

    # save the filesize as well
    resource.size = get_resource_size(resource)
    resource.save()

def resource_supports_pagination(resource_type_str):
    logger.info('Check if resource type "{t}" supports pagination.'.format(
        t = resource_type_str
    ))
    return _resource_supports_pagination(resource_type_str)