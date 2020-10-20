class DataResource(object):

    # these are the keys of the dict that is submitted to the
    # ResourceMetadata deserializer.
    OBSERVATION_SET = 'observation_set'
    FEATURE_SET = 'feature_set'
    PARENT_OP = 'parent_operation'
    RESOURCE = 'resource'

    @classmethod
    def validate_type(cls, resource_path):
        raise NotImplementedError('You must'
        ' implement this method in the derived class')

    def get_contents(self, resource_path, limit=None):
        return None

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
