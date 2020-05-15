# This file contains information about the different 
# sequence-based file types and methods for validating them

from .base import DataResource


class SequenceResource(DataResource):
    '''
    This class is used to represent sequence-based files
    such as Fasta, Fastq, SAM/BAM

    We cannot reasonably validate the contents of these files quickly,
    so any validation will have to be deferred or queued somehow.

    This class will contain any logic common to these types
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass


class FastAResource(SequenceResource):
    '''
    This resource type is for Fasta files,
    compressed or not
    '''
    file_extensions = [
        'fasta',
        'fasta.gz',
        'fa',
        'fa.gz'
    ]

    @classmethod
    def validate_type(cls, resource_path):
        pass

class FastQResource(SequenceResource):
    '''
    This resource type is for Fastq files,
    compressed or not
    '''
    file_extensions = [
        'fastq',
        'fastq.gz',
        'fq',
        'fq.gz'
    ]

    @classmethod
    def validate_type(cls, resource_path):
        pass


class AlignedSequenceResource(SequenceResource):
    '''
    This is for SAM/BAM files
    '''
    file_extensions = [
        'bam',
        'sam'
    ]

    @classmethod
    def validate_type(cls, resource_path):
        pass