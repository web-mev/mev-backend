import logging

from .base import DataResource

from .sequence_types import FastAResource, \
    FastQResource, \
    AlignedSequenceResource

from .table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    FeatureTable, \
    BEDFile

logger = logging.getLogger(__name__)

# expose these keys for consistent reference outside of this package:
OBSERVATION_SET_KEY = DataResource.OBSERVATION_SET
FEATURE_SET_KEY = DataResource.FEATURE_SET
PARENT_OP_KEY = DataResource.PARENT_OP
RESOURCE_KEY = DataResource.RESOURCE

# A list of tuples for use in the database.
# The first item in each tuple is the stored value
# in the database.  The second is the "human-readable"
# strings that will be used in the UI:
DATABASE_RESOURCE_TYPES = [
    ('FQ', 'Fastq'),
    ('FA','Fasta'),
    ('ALN','Alignment (SAM/BAM)'),
    #('TBL','General data table'),
    ('FT', 'Feature table'),
    ('MTX','Numeric table'),
    ('I_MTX','Integer table'),
    ('ANN','Annotation table'),
    ('BED','BED-format file')
]


DB_RESOURCE_STRING_TO_HUMAN_READABLE = {
    x[0]:x[1] for x in DATABASE_RESOURCE_TYPES
}


HUMAN_READABLE_TO_DB_STRINGS = {
    x[1]:x[0] for x in DATABASE_RESOURCE_TYPES
}

# A mapping of the database strings to the classes
# needed to implement the validation.
RESOURCE_MAPPING = {
    'FQ': FastQResource, 
    'FA': FastAResource,
    'ALN': AlignedSequenceResource,
    #'TBL': TableResource,
    'FT': FeatureTable,
    'MTX': Matrix,
    'I_MTX': IntegerMatrix,
    'ANN': AnnotationTable,
    'BED': BEDFile
} 

# These types are skipped when files are validated.
# Files are inferred to be of these types based on 
# their file extensions.  Each resource type has a set
# of canonical extensions as a class member.  We check
# against those types when determining whether to skip
# validation. For example, if a file ends with "fastq.gz"
# we infer that it is a FastQResource as "fastq.gz" is one
# of the canonical extensions of the FastQResource class.
RESOURCE_TYPES_WITHOUT_VALIDATION = set([
    FastAResource,
    FastQResource,
    AlignedSequenceResource
])

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

def get_preview(resource_path, resource_type):
    '''
    Returns a JSON-format "preview" of the data
    underlying a Resource.  

    Assumes the resource_path arg is local to the 
    machine.
    '''

    # The resource type is the shorthand identifier.
    # To get the actual resource class implementation, we 
    # use the RESOURCE_MAPPING dict
    try:
        resource_class = RESOURCE_MAPPING[resource_type]
    except KeyError as ex:
        logger.error('Received a Resource that had a non-null resource_type'
            ' but was also not in the known resource types.'
        )
        return {'error': 'No preview available'}
        
    # instantiate the proper class for this type:
    resource_type = resource_class()
    preview = resource_type.get_preview(resource_path)
    return preview

def extension_is_consistent_with_type(filename, resource_type):
    '''
    Checks that the file extension is consistent with the 
    resource type.  Matching is case-insensitive

    `filename` is the name of the uploaded file (not a full path)
    `resource_type` is one of the keys in RESOURCE_MAPPING.  It 
    is assumed to have already been checked (the serializer from the 
    request validated it already)

    Also checks for a period/dot prior to the suffix.  Thus,
    if the filename was foobartsv and we were checking the "tsv"
    extension, this function would return False.  foobar.tsv would
    return True
    '''
    resource_class = RESOURCE_MAPPING[resource_type]
    for ext in resource_class.ACCEPTABLE_EXTENSIONS:
        n = len(ext)
        suffix = filename[(-n-1):].lower()
        if suffix == '.' + ext.lower():
            return True
    return False