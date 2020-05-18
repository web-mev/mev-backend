# This file contains information about the different table-
# based file types and methods for validating them

from .base import DataResource


class TableResource(DataResource):
    '''
    This is the most generic form of a delimited file.  Any
    type of data that can be represented as rows and columns.
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass


class Matrix(TableResource):
    '''
    This is a table that has only numeric types, possibly mixed
    types like floats and integers
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass


class IntegerMatrix(Matrix):
    '''
    This type further specializes the Matrix
    to admit only integers.
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass


class AnnotationTable(TableResource):
    '''
    This is a special type of table that will be responsible
    for annotating samples (e.g. adding sample names and 
    associated attributes like experimental group or other covariates)
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass


class BEDFile(TableResource):
    '''
    A file format that corresponds to the BED format.  This is
    the minimal BED format, which has:
    - chromosome
    - start position
    - end position
    '''
    @classmethod
    def validate_type(cls, resource_path):
        pass