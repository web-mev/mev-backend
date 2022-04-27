WILDCARD = '*'

class ParseException(Exception):
    '''
    For raising exceptions when the parser
    fails for someon reason.
    '''
    pass

class UnexpectedTypeValidationException(Exception):
    '''
    Raised when a Resource fails to validate but *should have*
    been fine. 

    This would be raised, for instance, when an Operation completes and
    produces some output file, for which we know the type.  In that case,
    a failure to validate would indicate some unexpected error 
    '''
    pass

class DataResource(object):

    # these are the keys of the dict that is submitted to the
    # ResourceMetadata deserializer.
    OBSERVATION_SET = 'observation_set'
    FEATURE_SET = 'feature_set'
    PARENT_OP = 'parent_operation'
    RESOURCE = 'resource'

    STANDARD_FORMAT = ''

    def validate_type(self, resource_path, file_extension):
        raise NotImplementedError('You must'
        ' implement this method in the derived class')

    def performs_validation(self):
        '''
        Certain types of files (e.g. fastq) are laborious
        to validate or we cannot reliably check those. To 
        prevent localization of large DataResources that skip
        validation, we expose this method.

        By default, return False, which asserts that the resource
        type does not implement validation methods. It is the job
        of the child classes to implement this method if they are
        able to perform validation
        '''
        return False


    def get_contents(self, resource_path, file_extension, query_params={}):
        raise NotImplementedError('You must'
        ' implement this method in the derived class')

    def extract_metadata(self, resource_path, file_extension, parent_op_pk=None):
        raise NotImplementedError('You must'
        ' implement this method in the derived class')
        
    @staticmethod
    def get_extension(path):
        '''
        A single method to return the extension of the file. By convention,
        the lower-cased contents AFTER the final dot/period.
        '''
        return path.split('.')[-1].lower()

    @staticmethod
    def get_paginator():
        raise NotImplementedError('Must override this method in a subclass.')

    def setup_metadata(self, ):
        '''
        This sets up the basic dict that will eventually be submitted
        to the ResourceMetadata deserializer.  Child classes will
        fill-in the fields as appropriate.
        '''
        self.metadata = {
            DataResource.PARENT_OP: None,
            DataResource.OBSERVATION_SET: None,
            DataResource.FEATURE_SET: None,
            DataResource.RESOURCE: None
        }

    def save_in_standardized_format(self, resource_path, resource_name, file_extension):
        '''
        This method is used for saving user-supplied resources/files as something
        we can consistently refer to. For instance, users may load csv, tsv, excel, etc.
        files for data. In the analyses, we don't want to constantly be checking for
        how to parse these types. Hence, for table-based resources, we simply rewrite the
        file as a TSV so that all analyses can safely assume they will be given a valid
        TSV-format file.

        In this base-class implementation, we don't do anything- just echo back.
        '''
        return (resource_path, resource_name)

