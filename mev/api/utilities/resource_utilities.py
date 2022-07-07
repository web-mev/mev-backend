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
    get_standard_format, \
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

    if resource.owner == user:
        if not resource.is_active:
            raise InactiveResourceException()
        # requester can access, resource is active. Return the instance
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
    raise NoResourceFoundException('Could not find any resource'
        ' identified by the ID {u}'.format(u=resource_pk)
    )

def delete_resource_by_pk(resource_pk):
    '''
    Deletes the database record. Does NOT delete the associated
    file.

    Note that this does not perform any logic on deletion. For instance, 
    one might want to protect deletion of critical files. That logic should
    be implemented elsewhere.
    '''
    logger.info('Attempt to delete the Resource database model identified'
        ' by pk={pk}'.format(pk=str(resource_pk))
    )
    r = get_resource_by_pk(resource_pk)
    logger.info('Resource ({pk}) was found.'.format(pk=str(resource_pk)))
    try:
        r.delete()
    except Exception as ex:
        message = 'Failed to delete Resource ({pk}) from the database.'
        logger.info(message)
        alert_admins(message)

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
        local_path = localize_resource(resource_instance)
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
        logger.info('Resource metadata was valid. Now save it.')
        try:
            rm = rms.save()
            rm.save()
        except OperationalError as ex:
            message = ('Caught an OperationalError when trying to'
                ' save metadata for resource with pk={pk}'.format(
                    pk=resource.pk
                )
            )
            logger.info(message)

            # if the save failed (e.g. perhaps b/c it was too large)
            # then just fill in blank metadata.
            rms = ResourceMetadataSerializer(data=d)
            if rms.is_valid():
                rm = rms.save()
                rm.save()
            alert_admins(message)

        except Exception as ex:
            message = ('Caught an unexpected error when trying to save metadata'
                ' for resource with pk={pk}'.format(pk=resource.pk)
            )
            logger.info(message)          
            rms = ResourceMetadataSerializer(data=d)
            if rms.is_valid():
                rm = rms.save()
                rm.save()
            alert_admins(message)

def move_resource_to_final_location(resource_instance):
    '''
    resource_instance is the database object
    '''
    try:
        return get_storage_backend().store(resource_instance)
    except Exception as ex:
        message = Resource.UNEXPECTED_STORAGE_ERROR
        raise Exception(message)

def get_resource_size(resource_instance):
    return get_storage_backend().get_filesize(resource_instance.path)

def localize_resource(resource_instance):
    '''
    Return the local path to the resource. The storage backend handles the act of
    moving the file to our local cache
    '''
    # first check if the file might already be local.
    if os.path.exists(resource_instance.path):
        return resource_instance.path
        
    try:
        return get_storage_backend().localize_resource(resource_instance)
    except FileNotFoundError:
        message = ('File corresponding to Resource ({pk}) was not found'
            ' in the final storage location ({path}).'
            ' Please check this.'.format(
                pk = str(resource_instance.pk),
                path = resource_instance.path
            )
        )
        logger.info(message)
        raise Exception(message)
    except Exception as ex:
        logger.info('Caught an unexpected exception when localizing the resource.')
        raise ex

def retrieve_metadata(resource_path, resource_class_instance):

    # Note that the metadata could fail for type issues and we have to plan
    # for failures there. For instance, a table can be compliant, but the 
    # resulting metadata could violate a type constraint (e.g. if a string-based
    # attribute does not match our regex, is too long, etc.)
    try:
        return resource_class_instance.extract_metadata(resource_path)
    except ValidationError as ex:
        logger.info('Caught a ValidationError when extracting metadata from'
            ' resource at path: {p}'.format(p=resource_path)
        )
        err_list = []
        for k,v in ex.get_full_details().items():
            # v is a nested dict
            msg = v['message']
            err_str = '{k}:{s}'.format(k=k, s = str(msg))
            err_list.append(err_str)
        raise ResourceValidationException(
            Resource.ERROR_WITH_REASON.format(ex=','.join(err_list))
        )
    except Exception as ex:
        logger.info('Encountered an exception when extracting metadata: {ex}'.format(
            ex = ex
        ))
        raise Exception('Encountered an unexpected issue when extracting metadata.'
            ' An administrator has been notified.'
        )

def handle_valid_resource(resource,
        resource_class_instance,
        local_path):
    '''
    Once a Resource has been successfully validated, this function does some
    final operations such as moving the file and extracting metadata.

    `resource` is the database object
    `resource_class_instance` is an instantiated object that implements 
        the particular resource type logic
    `local_path` is a path to the standard-format file which is located
        on this local filesystem.
    '''
        
    # get the metadata. Any problems will raise exceptions which we allow to
    # percolate up the stack.
    metadata = retrieve_metadata(local_path, resource_class_instance)

    # attempt to associate the metadata with the resource. If this fails, an
    # exception will be raised, which we allow to percolate up.
    add_metadata_to_resource(resource, metadata)

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
        err = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
            requested_resource_type = requested_resource_type
        )
        raise ResourceValidationException(err)

def retrieve_resource_class_standard_format(requested_resource_type):
    '''
    This returns the standard format for a resource type
    
    The `requested_resource_type` arg is the shorthand identifier.
    The return value is the standard format (a shorthand ID like "TSV")
    '''
    try:
        return get_standard_format(requested_resource_type)
    except KeyError as ex:
        err = Resource.UNKNOWN_RESOURCE_TYPE_ERROR.format(
            requested_resource_type = requested_resource_type
        )
        raise Exception(err)

def check_if_resource_unset(resource_instance):
    '''
    We depend on both the resource type and format fields to be set for a file
    to be deemed 'valid'. This utlity function checks that and returns a boolean
    indicating whether its validity has been established prior.
    '''
    resource_type_set = (resource_instance.resource_type is not None) \
        and (len(resource_instance.resource_type) > 0)

    file_format_set = (resource_instance.file_format is not None) \
        and (len(resource_instance.file_format) > 0)
        
    previously_unset = (not resource_type_set) and (not file_format_set)
    return previously_unset

def handle_invalid_resource(resource_instance, requested_resource_type, requested_file_format, message = None):

    # "convert" the None to an empty string
    message = message if message else ''

    # was the file previously valid? This affects whether we revert to that prior
    # state or simply report that the file cannot be validated given the current type/format
    previously_unset = check_if_resource_unset(resource_instance)

    # If resource_type has not been set (i.e. it is None), then this   
    # Resource has NEVER been verified.  We report a failure
    # via the status message and set the appropriate flags
    if previously_unset:
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
        # an INvalid type or format.  In this case, revert back to the
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
            requested_file_format = requested_file_format,
            original_resource_type = hr_original_resource_type,
            file_format = resource_instance.file_format
        )
        status_msg = status_msg + ' ' + message        
        resource_instance.status = status_msg

def perform_validation(resource_instance, 
    resource_type_class, file_format, local_path):
    '''
    Calls the validation function on the particular resource type.

    Note that validation failure means that we were able to read/parse
    and yet the file did not meet our expectations. This is distinct from
    an exception due to an unexpected issue.

    If something unexpected goes wrong, an exception will be raised.
    If the file fails to validate, will return a tuple of (False, message)
    where `message` is a helpful reason for that failure to validate.
    If the file successfully validates, will return a tuple of (True, message)
    where message is typically an empty string since there's nothing to report.
    '''

    try:
        is_valid, message = resource_type_class.validate_type(
            local_path, file_format)
        return is_valid, message
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

def initiate_resource_validation(resource_instance, requested_resource_type, file_format):
    '''
    This function orchestrates the resource validation process.
    Use this function to initiate the resource validation process 
    
    If ANY part of the validation fails, the requested changes to
    the resource will not be persisted.

    Predictable errors in the validation process should raise 
    ResourceValidationException, providing a helpful reason for that failure.
    '''

    logger.info('Validate resource {x} against requested'
        ' type of {t} with format {f}'.format(
        x = str(resource_instance.id),
        t = requested_resource_type,
        f = file_format
    ))

    # If we do not have BOTH the resource type and file format, then
    # we immediately return since we can't validate.
    if (requested_resource_type is None) or (file_format is None):
        resource_instance.status = Resource.UNABLE_TO_VALIDATE
        resource_instance.save()
        return

    # check the file format is consistent with the requested type:
    check_file_format_against_type(requested_resource_type, file_format)

    # Get the resource class. If not found, exceptions are raised
    resource_class_instance = retrieve_resource_class_instance(requested_resource_type)

    if resource_class_instance.performs_validation():
        logger.info('Since the resource class permits validation, go and'
            ' validate this resource.')
            
        # We need to localize the file to validate it.
        local_path = localize_resource(resource_instance)

        is_valid, message = perform_validation(
            resource_instance, resource_class_instance, file_format, local_path)
    else:
        # resource type does not include validation. It's "valid" by default
        is_valid = True
        local_path = resource_instance.path # doesn't matter

    if is_valid:
        # the resource was valid, so first save it in our standardized format
        # `standardized_format_path` can be the path to the standardized file 
        # in a tmp location OR equivalent to the existing `local_path` if the 
        #file is already in the standard format for the resource type
        logger.info('The local path prior to standardization is: {p}'.format(p=local_path))
        standardized_format_path = resource_class_instance.save_in_standardized_format(local_path, \
            file_format)
        logger.info('The local path after to standardization is: {p}'.format(
            p=standardized_format_path))

        handle_valid_resource(resource_instance, \
            resource_class_instance, \
            standardized_format_path)

        # set the path attribute since the `move_resource_to_final_location`
        # function uses that
        resource_instance.path = standardized_format_path
        final_path = move_resource_to_final_location(resource_instance)

        # we can now save the api.models.Resource instance since everything
        # validated and worked properly
        resource_instance.path = final_path
        resource_instance.resource_type = requested_resource_type
        resource_instance.file_format = resource_class_instance.STANDARD_FORMAT
        resource_instance.size = get_resource_size(resource_instance)
        resource_instance.status = Resource.READY
    else:
        logger.info('Resource ({pk}) failed validation for {rt}, {ff}'.format(
            pk = resource_instance.pk,
            rt = requested_resource_type,
            ff = file_format
        )
        )
        handle_invalid_resource(resource_instance, requested_resource_type, file_format, message)

    # save changes    
    resource_instance.save()

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