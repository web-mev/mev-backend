# This module defines constants that may be required to be 
# accessed across several apps

WILDCARD = '*'

# The following are 'shorthand' IDs for identifying the
# file/resource types in the database. They are also used to map
# particular resource types to their validation logic
# in the `resource_types` package.
FASTQ_KEY = 'FQ'
FASTA_KEY = 'FA'
ALIGNMENTS_KEY = 'ALN'
FEATURE_TABLE_KEY = 'FT'
MATRIX_KEY = 'MTX'
INTEGER_MATRIX_KEY = 'I_MTX'
EXPRESSION_MATRIX_KEY = 'EXP_MTX'
RNASEQ_COUNT_MATRIX_KEY = 'RNASEQ_COUNT_MTX'
NETWORK_DESCRIPTOR_KEY = 'NS'
ANNOTATION_TABLE_KEY = 'ANN'
BED_FILE_KEY = 'BED'
JSON_FILE_KEY = 'JSON'
GENERAL_FILE_KEY = WILDCARD 

# To use with the database, we need a list of tuples connecting
# the shorthand IDs with the human-readable values:
DATABASE_RESOURCE_TYPES = [
    (FASTQ_KEY, 'Fastq'),
    (FASTA_KEY,'Fasta'),
    (ALIGNMENTS_KEY,'Alignment (SAM/BAM)'),
    (FEATURE_TABLE_KEY, 'Feature table'),
    (MATRIX_KEY,'Numeric table'),
    (INTEGER_MATRIX_KEY,'Integer table'),
    (EXPRESSION_MATRIX_KEY,'Expression matrix'),
    (RNASEQ_COUNT_MATRIX_KEY,'RNA-seq count matrix'),
    (NETWORK_DESCRIPTOR_KEY, 'Network descriptor'),
    (ANNOTATION_TABLE_KEY,'Annotation table'),
    (BED_FILE_KEY,'BED-format file'),
    (JSON_FILE_KEY,'JSON-format file'),
    (GENERAL_FILE_KEY, 'General file')
]

# For better messages, logging, etc. prepare a map
# based on the list of tuples above.
DB_RESOURCE_KEY_TO_HUMAN_READABLE = {
    x[0]:x[1] for x in DATABASE_RESOURCE_TYPES
}

# These constants are related to metadata (api.models.ResourceMetadata)
# which can be associated with api.models.Resource instances
OBSERVATION_SET_KEY = 'observation_set'
FEATURE_SET_KEY = 'feature_set'
PARENT_OP_KEY = 'parent_operation'
RESOURCE_KEY = 'resource'