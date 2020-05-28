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
    compressed or not. Fastq files are recognized using
    the following formats:

    - fastq
    - fastq.gz
    - fq
    - fq.gz

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
    This resource type is for SAM/BAM files.  We accept
    both SAM and BAM files named using their canonical extensions:

    - ".bam" for BAM files
    - ".sam" for SAM files
    
    '''
    file_extensions = [
        'bam',
        'sam'
    ]

    @classmethod
    def validate_type(cls, resource_path):
        pass