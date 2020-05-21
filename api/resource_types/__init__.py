from .sequence_types import FastAResource, \
    FastQResource, \
    AlignedSequenceResource

from .table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    BEDFile

# A list of tuples for use in the database.
# The first item in each tuple is the stored value
# in the database.  The second is the "human-readable"
# strings that will be used in the UI:
DATABASE_RESOURCE_TYPES = [
    ('FQ', 'Fastq'),
    ('FA','Fasta'),
    ('ALN','Alignment (SAM/BAM)'),
    ('TBL','General data table'),
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
    'TBL': TableResource,
    'MTX': Matrix,
    'I_MTX': IntegerMatrix,
    'ANN': AnnotationTable,
    'BED': BEDFile
} 

def resource_type_is_valid(resource_class, resource_path):
    '''
    When a `Resource.resource_type` is set or edited, we need
    to validate that the type "agrees" with the file format.

    This function is the entrypoint for this validation.

    - `resource_class` is the implementation class which performs
    the validation
    - `resource_path` is the path to the file we are validating.
    '''
    pass
