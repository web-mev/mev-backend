import logging

from constants import UNSPECIFIED_FORMAT, \
    GENERAL_DESCRIPTION, \
    PARENT_OP_KEY

from .base import DataResource

logger = logging.getLogger(__name__)


class GeneralResource(DataResource):

    ACCEPTABLE_FORMATS = [
        UNSPECIFIED_FORMAT
    ]
    DESCRIPTION = GENERAL_DESCRIPTION
    
    def validate_type(self, resource_instance, file_format):
        '''
        Since we cannot validate an unknown type, simply return the trivial tuple
        indicating that it "passed" validation
        '''
        return (True, None)
       
    def extract_metadata(self, resource_instance, parent_op_pk=None):
        # call the super method to initialize the self.metadata
        # dictionary
        super().setup_metadata()

        # now add the information to self.metadata:
        if parent_op_pk:
            self.metadata[PARENT_OP_KEY] = parent_op_pk
        return self.metadata


    def get_contents(self, resource_instance, query_params={}):
        logger.info('Cannot use get_contents on an unknown type.')
        return None