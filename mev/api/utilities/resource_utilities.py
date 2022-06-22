import os
import uuid
import json
import logging

from django.utils.module_loading import import_string
from django.db.utils import OperationalError
from rest_framework.exceptions import ValidationError

from api.models import Resource, ResourceMetadata, ExecutedOperation, OperationResource
from api.exceptions import AttributeValueError, \
    StorageException, \
    ResourceValidationException
from api.serializers.resource_metadata import ResourceMetadataSerializer
from .basic_utils import make_local_directory, \
    move_resource, \
    copy_local_resource
from api.data_structures.attributes import DataResourceAttribute
from api.storage_backends import get_storage_backend
from api.storage_backends.helpers import get_storage_implementation
from constants import DB_RESOURCE_KEY_TO_HUMAN_READABLE, \
    RESOURCE_KEY
from resource_types import get_contents, \
    get_resource_paginator as _get_resource_paginator, \
    format_is_acceptable_for_type, \
    resource_supports_pagination as _resource_supports_pagination, \
    get_acceptable_formats, \
    get_resource_type_instance, \
    RESOURCE_TYPES_WITHOUT_CONTENTS_VIEW, \
    RESOURCE_MAPPING
from api.exceptions import NoResourceFoundException, \
    InactiveResourceException, \
    OwnershipException
from api.utilities.admin_utils import alert_admins

logger = logging.getLogger(__name__)

def check_resource_request_validity(user, resource_pk):
    '''
    Used by several api endpoints that need access to a user's resource.
    This function validates that the resource is such that
    the user is able to access/modify it.

    Returns a resource instance or a specific flag which indicates
    the type of issue to the caller.
    '''
    resource = get_resource_by_pk(resource_pk)

    if user.is_staff or (resource.owner == user):
        if not resource.is_active:
            raise InactiveResourceException()
        # requester can access, resource is active.  Go get preview
        return resource
    else:
        raise OwnershipException()

def check_that_resource_exists(path):
    '''
    Given a path, return a boolean indicating whether
    the file at the specified path exists.
    '''
    return get_storage_backend().resource_exists(path) 

def get_resource_by_pk(resource_pk):

    try:
        resource = Resource.objects.get(pk=resource_pk)
        return resource
    except Resource.DoesNotExist as ex:
        logger.info('Received an unknown/invalid primary key'
            ' when trying to retrieve a Resource instance.'
            ' Try looking for OperationResource with the UUID ({u}).'.format(
                u = resource_pk
            )
        )
    try:
        resource = OperationResource.objects.get(pk=resource_pk)
        return resource
    except OperationResource.DoesNotExist as ex:
        logger.info('Could not find an OperationResource with'
            ' pk={u}'.format(u = resource_pk)
        )

    # If we are here, raise an exception since nothing was found    
    raise NoResourceFoundException('Could not find any sublcasses of AbstractResource'
        ' identified by the ID {u}'.format(u=resource_pk)
    )

def delete_resource_by_pk(resource_pk):

    try:
        resource = Resource.objects.get(pk=resource_pk)
        resource.delete()
    except Resource.DoesNotExist as ex:
        logger.info('Received an unknown/invalid primary key'
            ' when trying to retrieve a Resource instance.'
            ' Try looking for OperationResource with the UUID ({u}).'.format(
                u = resource_pk
            )
        )
    try:
        resource = OperationResource.objects.get(pk=resource_pk)
        resource.delete()
    except OperationResource.DoesNotExist as ex:
        logger.info('Could not find an OperationResource with'
            ' pk={u}'.format(u = resource_pk)
        )

    # If we are here, raise an exception since nothing was found    
    raise NoResourceFoundException('Could not find any sublcasses of AbstractResource'
        ' identified by the ID {u}'.format(u=resource_pk)
    )

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
        local_path = get_local_resource_path(resource_instance)
        return get_contents(local_path,
                resource_instance.resource_type,
                resource_instance.file_format, 
                query_params)

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
        logger.info('Resource had some existing metadata, so update.')
    except ResourceMetadata.DoesNotExist:
        logger.info('Resource did not previously have metadata attached.')
        rms = ResourceMetadataSerializer(data=metadata)
    if rms.is_valid(raise_exception=True):
        try:
            rm = rms.save()
            rm.save()
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
    try:
        return get_storage_backend().store(resource_instance)
    except Exception as ex:
        # alert_admins('A backend storage failure occurred for resource'
        #     ' with pk={x}'.format(x=resource_instance.pk)
        # )
        resource_instance.status = Resource.UNEXPECTED_STORAGE_ERROR
        # Since this was an unexpected issue with storing the item, we
        # effectively disable the resource. Otherwise, unexpected things
        # can happen downstream
        resource_instance.save()
        raise ex

def get_resource_size(resource_instance):
    return get_storage_backend().get_filesize(resource_instance.path)

def get_local_resource_path(resource_instance):
    '''
    Return the local path to the resource. The storage backend handles the act of
    moving the file to our local cache
    '''
    return get_storage_backend().get_local_resource_path(resource_instance)

def handle_valid_resource(
        resource, 
        resource_class_instance, 
        requested_resource_type,
        file_format):
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
        try:
            local_path = get_local_resource_path(resource)
        except Exception as ex:
            # We know something went wrong, but here modify the error message to be more user
            # friendly for display purposes.
            raise Exception('Failed following successful validation. An unexpected issue occurred when'
                ' moving the file. An administrator has been notified. This may be a temporary error,'
                ' so you may try again to validate.'
            )

        logger.info('The local path prior to standardization is: {p}'.format(p=local_path))

        # the resource was valid, so first save it in our standardized format
        new_path, new_name = resource_class_instance.save_in_standardized_format(local_path, \
            resource.name, resource.file_format)

        # need to know the "updated" file extension
        file_format = resource_class_instance.STANDARD_FORMAT

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
            resource.name = new_name

    else:
        # We are here if the resource type does not support validation.
        # Hence, since we did not have to perform any standardization, etc.
        # we simply set the necessary variables without change.
        new_path = resource.path
        new_name = resource.name

    # since the resource was valid, we can also fill-in the metadata
    # Note that the metadata could fail for type issues and we have to plan
    # for failures there. For instance, a table can be compliant, but the 
    # resulting metadata could violate a type constraint (e.g. if a string-based
    # attribute does not match our regex, is too long, etc.)
    try:
        metadata = resource_class_instance.extract_metadata(new_path, file_format)
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
        # don't want to set the resource type since the metadata failed as it sets up 
        # inconsistencies between the validation of a format and its "usability" in WebMeV
        # For instance, a compliant matrix could have excessively long sample names and we don't
        # want to permit that.
        resource.resource_type = None
        raise Exception(
            Resource.ERROR_WITH_REASON.format(ex=','.join(err_list))
        )
    except Exception as ex:
        logger.info('Encountered an exception when extracting metadata: {ex}'.format(
            ex = ex
        ))
        resource.resource_type = None
        raise Exception('Encountered an unexpected issue when extracting metadata.'
            ' An administrator has been notified.'
        )

    try:
        add_metadata_to_resource(resource, metadata)
        resource.status = Resource.READY
    except Exception as ex:
        resource.resource_type = None
        raise Exception('Encountered an unexpected issue when adding metadata to the resource.'
            ' An administrator has been notified.'
        )

    try:
        # have to send the file to the final storage. If we are using local storage
        # this is trivial. However, if we are using remote storage, the data saved
        # in the standardized format needs to be pushed there also.
        final_path = move_resource_to_final_location(resource)

        # Only at this point (when we have successfully validated, moved, extracted metadata, etc.)
        # do we set the new path and resource type on the database object.
        resource.path = final_path
        resource.resource_type = requested_resource_type
        resource.file_format = file_format
    except Exception as ex:
        logger.info('Exception when moving valid final resource after extracting/appending metadata.'
            ' Exception was {ex}'.format(ex=str(ex))
        )
        resource.resource_type = None
        raise Exception('Encountered an unexpected issue when moving your validated resource.'
            ' An administrator has been notified. You may also attempt to validate again.'
        )

def check_file_format_against_type(requested_resource_type, file_format):
    '''
    Checks that the file format is consistent with the requested
    resource type. Each resource type permits a certain set of expected
    file formats.  If not, raise an ResourceValidationException

    If the chosen format and type are acceptable, simply return
    
    `resource` is an instance of the db model (`api.models.Resource`)
    `requested_resource_type` is the shorthand ID (e.g. 'MTX')
    `file_format` is a shorthand for the format (e.g. 'tsv')
    '''
    try:
        acceptable_format = format_is_acceptable_for_type(file_format, requested_resource_type)
    except KeyError as ex:
        ex = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
            requested_resource_type = requested_resource_type
        )
        raise ResourceValidationException(ex)

    if not acceptable_format:
        acceptable_extensions = ','.join(get_acceptable_formats(requested_resource_type))
        ex = Resource.UNKNOWN_FORMAT_ERROR.format(
            readable_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[requested_resource_type],
            fmt = file_format,
            extensions_csv = acceptable_extensions
        )
        raise ResourceValidationException(ex)

def retrieve_resource_class_instance(requested_resource_type):
    '''
    This returns an actual resource class implementation from
    the resource_types package
    
    The `requested_resource_type` arg is the shorthand identifier.
    '''
    try:
        return get_resource_type_instance(requested_resource_type)
    except KeyError as ex:
        ex = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
            requested_resource_type = requested_resource_type
        )
        raise ResourceValidationException(ex)

def handle_invalid_resource(resource_instance, requested_resource_type, message = ''):

    # If resource_type has not been set (i.e. it is None), then this   
    # Resource has NEVER been verified.  We report a failure
    # via the status message and set the appropriate flags
    if resource_instance.resource_type is None:
        status_msg = Resource.FAILED.format(
            requested_resource_type=DB_RESOURCE_KEY_TO_HUMAN_READABLE[
                requested_resource_type]
        )
        status_msg = status_msg + ' ' + message
        resource_instance.status = status_msg
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
        hr_requested_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[
            requested_resource_type]
        hr_original_resource_type = DB_RESOURCE_KEY_TO_HUMAN_READABLE[
            resource_instance.resource_type]

        # ...and compose the status message
        status_msg = Resource.REVERTED.format(
            requested_resource_type= hr_requested_resource_type,
            original_resource_type = hr_original_resource_type
        )
        status_msg = status_msg + ' ' + message        
        resource_instance.status = status_msg
    
def validate_resource(resource_instance, requested_resource_type, file_format):
    '''
    This function performs validation against the requested resource
    type and format.  
    
    If ANY part of the validation fails, the requested changes to
    the resource will not be persisted.

    Predictable errors in the validation process should raise 
    ResourceValidationException, providing a helpful reason for that failure.
    '''

    # If we do not have BOTH the resource type and file format, then
    # we immediately return since we can't validate.
    if (requested_resource_type is None) or (file_format is None):
        resource_instance.status = Resource.UNABLE_TO_VALIDATE
        resource_instance.save()
        return

    # Start the process...
    logger.info('Validate resource {x} against requested'
        ' type of {t} with format {f}'.format(
        x = str(resource_instance.id),
        t = requested_resource_type,
        f = file_format
    ))

    # check the file format is consistent with the requested type:
    check_file_format_against_type(requested_resource_type, file_format)

    # Get the resource class. If not found, exceptions are raised
    resource_class_instance = retrieve_resource_class_instance(requested_resource_type)
    
    if resource_class_instance.performs_validation():

        logger.info('Since the resource class permits validation, go and'
            ' validate this resource.')

        # Regardless of whether we are validating a new upload or changing the type
        # of an existing file, the file is already located at its "final" location
        # which is dependent on the storage backend.  Now, if the storage backend
        # is remote (e.g. bucket storage), we need to pull the file locally to 
        # perform validation.
        # Note that failures to pull the file locally will raise an exception, which we 
        # catch and respond to
        try:
            local_path = get_local_resource_path(resource_instance)
        except Exception as ex:
            # We know something went wrong, but here modify the error message to be more user
            # friendly for display purposes.
            raise Exception('Failed during validation. An unexpected issue occurred when'
                ' moving the file for inspection. An administrator has been notified. You may'
                ' attempt to validate again.'
            )

        try:
            is_valid, message = resource_class_instance.validate_type(
                local_path, file_format)
        except Exception as ex:
            # It's expected that files can be invalid. What is NOT expected, however,
            # are general Exceptions that can be raised due to unforeseen issues 
            # that could occur duing the validation. Catch those
            logger.info('An exception was raised when attempting to validate'
                ' the Resource {pk} located at {local_path}'.format(
                    pk = str(resource_instance.pk),
                    local_path = local_path
                )
            )
            raise Exception(Resource.UNEXPECTED_VALIDATION_ERROR)   

    else: # resource type does not include validation
        is_valid = True

    if is_valid:
        handle_valid_resource(resource_instance, resource_class_instance, requested_resource_type, file_format)
    else:
        if message and len(message) > 0:
            handle_invalid_resource(resource_instance, requested_resource_type, message)
        else:
            handle_invalid_resource(resource_instance, requested_resource_type)

def validate_and_store_resource(resource, requested_resource_type, file_format):

    # move the file backing this Resource.
    # Note that we do this BEFORE validating so that the validation functions don't
    # have to contain different steps for handling new uploads or requests to
    # change the type of a Resource.  By immediately moving the file to its 
    # final storage backend, we can handle all the variations in the same manner.
    # If the `move_resource_to_final_location` function does not succeed, it will
    # raise an exception which we allow to percolate. The proper attributes
    # are set on `resource` to properly denote that failure, so we don't do anything here
    resource.path = move_resource_to_final_location(resource)
   
    try:
        validate_resource(resource, requested_resource_type, file_format)
        # save the filesize as well
        resource.size = get_resource_size(resource)
    except Exception as ex:
        resource.status = str(ex)
        alert_admins('Encountered an issue during resource validation and storage. See logs.')
    resource.is_active = True
    resource.save()

def resource_supports_pagination(resource_type_str):
    logger.info('Check if resource type "{t}" supports pagination.'.format(
        t = resource_type_str
    ))
    return _resource_supports_pagination(resource_type_str)

def write_resource(content, destination):
    '''
    Writing local files is not particularly common in MEV, but
    this is a central function which does all the "prep work"
    like checking that the local directory exists, etc.

    Note that this is a total rewrite, NOT an append (see the open mode below)
    '''
    storage_dir = os.path.dirname(destination)
    if not os.path.exists(storage_dir):

        # this function can raise an exception which will get
        # pushed up to the caller
        make_local_directory(storage_dir)

    assert(type(content) == str)
    with open(destination, 'w') as fout:
        fout.write(content)