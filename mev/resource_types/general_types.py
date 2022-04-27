import logging

from .base import DataResource, WILDCARD

logger = logging.getLogger(__name__)

class GeneralResource(DataResource):

    ACCEPTABLE_EXTENSIONS = [WILDCARD,]
    DESCRIPTION = 'A general file. Typically used to denote an unspecified type.'
    
    def validate_type(self, resource_path, file_extension):
        '''
        Since we cannot validate an unknown type, simply return the trivial tuple
        indicating that it "passed" validation
        '''
        return (True, None)
       
    def extract_metadata(self, resource_path, file_extension, parent_op_pk=None):
        # call the super method to initialize the self.metadata
        # dictionary
        super().setup_metadata()

        # now add the information to self.metadata:
        if parent_op_pk:
            self.metadata[DataResource.PARENT_OP] = parent_op_pk
        return self.metadata


    def get_contents(self, resource_path, file_extension, query_params={}):
        logger.info('Cannot use get_contents on an unknown type.')
        return None