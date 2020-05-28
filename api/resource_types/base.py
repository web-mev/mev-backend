# This package contains information about the different file types
# and methods for validating them

class DataResource(object):

    @classmethod
    def validate_type(cls, resource_path):
        raise NotImplementedError('You must'
        ' implement this method in the derived class')

    def get_preview(self, resource_path):
        return {'info': 'Previews not available for this resource type.'}