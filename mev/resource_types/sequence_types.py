# This file contains information about the different 
# sequence-based file types and methods for validating them

from .base import DataResource


class SequenceResource(DataResource):
    '''
    This class is used to represent sequence-based files
    such as Fasta, Fastq, SAM/BAM

    We cannot (reasonably) locally validate the contents of these 
    files quickly or exhaustively, so minimal validation is performed
    remotely
    '''
    @classmethod
    def validate_type(cls, resource_path):
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
            self.metadata[DataResource.PARENT_OP] = parent_op_pk


class FastAResource(SequenceResource):
    '''
    This type is for validating Fasta files,
    compressed or not.  Fasta files are recognized using
    the following formats:

    - fasta
    - fasta.gz
    - fa
    - fa.gz

    '''
    DESCRIPTION = 'FASTA-format sequence file.'

    ACCEPTABLE_EXTENSIONS = [
        'fasta',
        'fasta.gz',
        'fa',
        'fa.gz'
    ]

    def validate_type(self, resource_path):
        pass

class FastQResource(SequenceResource):
    '''
    This resource type is for Fastq files,
    compressed or not. Fastq files are recognized using
    the following formats:

    - fastq
    - fastq.gz
    - fq
    - fq.gz

    '''
    DESCRIPTION = 'FASTQ-format sequence file.  The most common format'\
        ' used for sequencing experiments.'

    ACCEPTABLE_EXTENSIONS = [
        'fastq',
        'fastq.gz',
        'fq',
        'fq.gz'
    ]

    def validate_type(self, resource_path):
        pass


class AlignedSequenceResource(SequenceResource):
    '''
    This resource type is for SAM/BAM files.  We accept
    both SAM and BAM files named using their canonical extensions:

    - ".bam" for BAM files
    - ".sam" for SAM files
    
    '''
    DESCRIPTION = 'BAM or SAM-format aligned sequence files.  Typically the' \
        ' output of an alignment process.'


    ACCEPTABLE_EXTENSIONS = [
        'bam',
        'sam'
    ]

    def validate_type(self, resource_path):
        pass