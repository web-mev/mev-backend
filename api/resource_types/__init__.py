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