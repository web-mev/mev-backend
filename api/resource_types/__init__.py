import logging

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