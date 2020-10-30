import logging

from api.models import Resource
from api.utilities.resource_utilities import get_resource_by_pk
from api.converters.mixins import CsvMixin, SpaceDelimMixin
from api.storage_backends import get_storage_backend

logger = logging.getLogger(__name__)

class BaseDataResourceConverter(object):
    
    def get_resource(self, resource_uuid):
        '''
        Given a UUID, get the Resource (database object) 
        '''
        return get_resource_by_pk(resource_uuid)

class LocalDataResourceConverter(BaseDataResourceConverter):
    '''
    This class holds actions/behavior for local-based Resources/files
    '''
    def get_local_path_from_uuid(self, resource_uuid):
        '''
        Given a UUID for a Resource, return a path to that file
        on the local filesystem
        '''
        r = self.get_resource(resource_uuid)
        local_path = get_storage_backend().get_local_resource_path(r)
        return local_path

class LocalDockerSingleDataResourceConverter(LocalDataResourceConverter):
    '''
    This converter takes a DataResource instance (for a single file,
    which is simply a UUID) and returns the path to 
    the local file.

    This converter takes that UUID, finds the Resource/file, brings it local, and returns
    the local path.
    '''
    def convert(self, user_input):
        '''
        user_input is the dictionary-representation of a api.data_structures.UserOperationInput
        '''
        resource_uuid = user_input
        return self.get_local_path_from_uuid(resource_uuid)


class LocalDockerMultipleDataResourceConverter(LocalDataResourceConverter):
    '''
    This converter takes a DataResource instance (for >1 file) and returns the path to 
    the local files as a list. Typically, this is then used with a mixin class to format
    the paths as a comma-delimited list, a space-delimited list, etc.

    For example, given the following DataResource:
    {
        'attribute_type': 'DataResource', 
        'value': [<UUID>, <UUID>, <UUID>]
    }

    This converter takes the list UUIDs, finds each Resource/file, brings it local, and returns
    a list of the local paths.
    '''

    def convert(self, user_input):
        path_list = []
        if type(user_input) == list:
            for u in user_input:
                path_list.append(self.get_local_path_from_uuid(u))
        elif type(user_input) == str:
            path_list.append(self.get_local_path_from_uuid(user_input))
        else:
            logger.error('Unrecognized type submitted for DataResource value: {v}'.format(
                v = value
            ))
        return path_list

class LocalDockerCsvResourceConverter(LocalDockerMultipleDataResourceConverter, CsvMixin):

    def convert(self, user_input):
        path_list = LocalDockerMultipleDataResourceConverter.convert(self, user_input)
        return CsvMixin.to_string(path_list)

class LocalDockerSpaceDelimResourceConverter(LocalDockerMultipleDataResourceConverter, SpaceDelimMixin):

    def convert(self, user_input):
        path_list = LocalDockerMultipleDataResourceConverter.convert(self, user_input)
        return SpaceDelimMixin.to_string(path_list)

class CromwellSingleDataResourceConverter(BaseDataResourceConverter):
    '''
    This converter takes a DataResource instance (for a single file) and returns the path to 
    the file in our cloud storage

    For example, given the following DataResource:
    {
        'attribute_type': 'DataResource', 
        'value': <UUID>
    }

    This converter takes that UUID, finds the Resource/file and returns
    the remote/cloud-based path.
    '''
    # TODO: note that if we are using the LocalStorage backend, we need to push files
    # to some kind of cloud-based storage first so that Cromwell can find them. 
    pass


class CromwellMultipleDataResourceConverter(BaseDataResourceConverter):
    '''
    This converter takes a DataResource instance (for >1 file) and returns the path to 
    the remote files as a list. Typically, this is then used with a mixin class to format
    the paths as a comma-delimited list, a space-delimited list, etc.

    For example, given the following DataResource:
    {
        'attribute_type': 'DataResource', 
        'value': [<UUID>, <UUID>, <UUID>], 
        'many': True, 
        'resource_types': ['MTX', 'I_MTX', 'EXP_MTX', 'RNASEQ_COUNT_MTX']
    }

    This converter takes the list UUIDs, finds each Resource/file and returns
    a list of the remote paths.
    '''
    pass