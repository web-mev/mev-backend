import logging

from .base import DataResource, ParseException, WILDCARD

from .sequence_types import FastAResource, \
    FastQResource, \
    AlignedSequenceResource

from .table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    Network, \
    AnnotationTable, \
    FeatureTable, \
    BEDFile

from .general_types import GeneralResource
from .json_types import JsonResource

logger = logging.getLogger(__name__)

# expose these keys for consistent reference outside of this package:
OBSERVATION_SET_KEY = DataResource.OBSERVATION_SET
FEATURE_SET_KEY = DataResource.FEATURE_SET
PARENT_OP_KEY = DataResource.PARENT_OP
RESOURCE_KEY = DataResource.RESOURCE

HUMAN_READABLE_TO_DB_STRINGS = {
    x[1]:x[0] for x in DATABASE_RESOURCE_TYPES
}

# A mapping of the database strings to the classes
# needed to implement the validation.
RESOURCE_MAPPING = {
    'FQ': FastQResource, 
    'FA': FastAResource,
    'ALN': AlignedSequenceResource,
    'FT': FeatureTable,
    'MTX': Matrix,
    'I_MTX': IntegerMatrix,
    'EXP_MTX': Matrix,
    'RNASEQ_COUNT_MTX': IntegerMatrix,
    'NS': Network,
    'ANN': AnnotationTable,
    'BED': BEDFile,
    'JSON': JsonResource,
    WILDCARD: GeneralResource
} 

# These types are skipped when files are validated.
# Files are inferred to be of these types based on 
# their file formats.  Each resource type has a set
# of canonical formats as a class member.  We check
# against those types when determining whether to skip
# validation. For example, if a file ends with "fastq.gz"
# we infer that it is a FastQResource as "fastq.gz" is one
# of the canonical formats of the FastQResource class.
RESOURCE_TYPES_WITHOUT_VALIDATION = set([
    FastAResource,
    FastQResource,
    AlignedSequenceResource,
    GeneralResource
])

# At minimum, those types that don't have validation methods also 
# will not return resource previews. For instance, we do not want to 
# produce the contents of a FASTQ file. 
RESOURCE_TYPES_WITHOUT_CONTENTS_VIEW = RESOURCE_TYPES_WITHOUT_VALIDATION

def get_resource_type_instance(resource_type_str):
    '''
    When a `Resource.resource_type` is set or edited, we need
    to validate that the type "agrees" with the file format.

    This function is the entrypoint for this validation.

    - `resource_type_class` is the implementation class which performs
    the validation
    - `resource_path` is the path to the file we are validating.

    Returns a tuple of (bool, str).
    The bool indicates whether the type was valid for the resource
    The string is a message providing an explanation for any failures.
    '''
    try:
        resource_type_class = RESOURCE_MAPPING[resource_type_str]
        return resource_type_class()
    except KeyError as ex:
        logger.error('Received an unknown resource_type identifier:'
            ' {resource_type}.  Current types are:'
            ' {resource_mapping}'.format(
                resource_mapping = ','.join(RESOURCE_MAPPING.keys()),
                resource_type = resource_type_str
            )
        )
        raise ex

def get_contents(resource_path, resource_type_str, file_format, query_params={}):
    '''
    Returns a "view" of the data underlying a Resource. The actual
    implementation of that view is prepared by the class corresponding
    to the resource type. 

    Note that to use properly with pagination, the returned object must support
    bracketed indexing (e.g. x[10:24]) and len() (and possibly other methods).
    We use the django.core.paginator.Paginator class, which expects 'list-like'
    arguments to be provided.

    Assumes the resource_path arg is local to the 
    machine.
    '''

    # The resource type is the shorthand identifier.
    # To get the actual resource class implementation, we 
    # use the RESOURCE_MAPPING dict
    try:
        resource_class = RESOURCE_MAPPING[resource_type_str]
    except KeyError as ex:
        logger.error('Received a Resource that had a non-null resource_type'
            ' but was also not in the known resource types.'
        )
        return {'error': 'No contents available'}
        
    # instantiate the proper class for this type:
    resource_type = resource_class()
    return resource_type.get_contents(resource_path, file_format, query_params)

def get_resource_paginator(resource_type_str):
    '''
    Returns a subclass of the django.core.paginator.Paginator class which 
    will respect their API so that all Resource types can be paginated in 
    a consistent manner
    '''
    # The resource type is the shorthand identifier.
    # To get the actual resource class implementation, we 
    # use the RESOURCE_MAPPING dict
    try:
        resource_class = RESOURCE_MAPPING[resource_type_str]
    except KeyError as ex:
        logger.error('Received a Resource that had a non-null resource_type'
            ' but was also not in the known resource types.'
        )
        return {'error': 'No contents available'}
        
    # instantiate the proper class for this type:
    resource_type = resource_class()
    return resource_type.get_paginator()

def resource_supports_pagination(resource_type_str):
    try:
        get_resource_paginator(resource_type_str)
        logger.info('Was able to successfully obtain a paginator')
        return True
    except NotImplementedError:
        logger.info('Failed to find a paginator class. Default to ignore'
            ' any requests for pagination.'
        )
        return False

def get_acceptable_formats(resource_type):
    '''
    Given the resource type "string", return a list of
    acceptable file formats for that type.
    '''
    resource_class = RESOURCE_MAPPING[resource_type]
    return resource_class.ACCEPTABLE_FORMATS

def format_is_consistent_with_type(file_format, resource_type):
    '''
    Checks that the file format (as denoted by a string) is consistent with the 
    resource type.  Matching is case-insensitive

    `file_format` is a string which denotes a resource's format,
    e.g. "tsv" for tab-delimited format.
    `resource_type` is one of the keys in RESOURCE_MAPPING.  It 
    is assumed to have already been checked (the serializer from the 
    request validated it already)
    '''
    try:
        acceptable_formats = get_acceptable_formats(resource_type)
    except KeyError as ex:
        logger.info('Received an unacceptable resource type {t}'
            ' when checking file format.'.format(t=ex)
        )
        message = 'Resource type {t} is not among the accepted types.'.format(t=ex)
        raise Exception(message)
    for ext in acceptable_formats:
        if ext == WILDCARD:
            return True
        if file_format.lower() == ext.lower():
            return True
    return False
