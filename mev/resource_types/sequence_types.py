# This file contains information about the different 
# sequence-based file types and methods for validating them

import logging

from constants import FASTQ_FORMAT, \
    FASTA_FORMAT, \
    BAM_FORMAT, \
    PARENT_OP_KEY

from .base import DataResource

logger = logging.getLogger(__name__)


class SequenceResource(DataResource):
    '''
    This class is used to represent sequence-based files
    such as Fasta, Fastq, SAM/BAM

    We cannot (reasonably) locally validate the contents of these 
    files quickly or exhaustively, so minimal validation is performed
    remotely
    '''
    @classmethod
    def validate_type(cls, resource_path, file_format):
        pass

    def extract_metadata(self, resource_path, parent_op_pk=None):
        '''
        For sequence-based types, we implement a trivial metadata
        extraction, as these resource types are not typically amenable
        to fast/easy parsing (possibly files that are many GB)

        Fill out an basic metadata object
        '''
        logger.info('Extracting metadata from resource with path ({path}).'.format(
            path = resource_path
        )) 

        # call the super method to initialize the self.metadata
        # dictionary
        super().setup_metadata()

        # now add the information to self.metadata:
        if parent_op_pk:
            self.metadata[PARENT_OP_KEY] = parent_op_pk



class FastAResource(SequenceResource):
    '''
    This type is for compressed Fasta files
    '''
    DESCRIPTION = 'FASTA-format sequence file.'

    ACCEPTABLE_FORMATS = [
        FASTA_FORMAT
    ]
    STANDARD_FORMAT = FASTA_FORMAT

    def validate_type(self, resource_path, file_format):
        pass

class FastQResource(SequenceResource):
    '''
    This resource type is for gzip-compressed Fastq files
    '''
    DESCRIPTION = 'FASTQ-format sequence file.  The most common format'\
        ' used for sequencing experiments. Should be GZIP compressed'\
        ' which is typically denoted with a "fastq.gz" file extension.'

    ACCEPTABLE_FORMATS = [
        FASTQ_FORMAT
    ]
    STANDARD_FORMAT = FASTQ_FORMAT

    def validate_type(self, resource_path, file_format):
        pass


class AlignedSequenceResource(SequenceResource):
    '''
    This resource type is for SAM/BAM files. 
    '''
    DESCRIPTION = 'BAM-format aligned sequence files.  Typically the' \
        ' output of an alignment process.'


    ACCEPTABLE_FORMATS = [
        BAM_FORMAT
    ]
    STANDARD_FORMAT = BAM_FORMAT

    def validate_type(self, resource_path, file_format):
        pass