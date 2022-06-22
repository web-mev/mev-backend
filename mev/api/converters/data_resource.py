import os
import logging

from api.models import Resource
from api.utilities.basic_utils import copy_local_resource
from api.utilities.resource_utilities import get_resource_by_pk, \
    localize_resource
from api.converters.mixins import CsvMixin, SpaceDelimMixin

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
        return localize_resource(r)

    def copy_local_resource_to_staging(self, resource_uuid, staging_dir):
        '''
        Takes a resource UUID and copies the associated file to `staging_dir`
        Returns a path to the copied file
        '''
        # this is the path to the user's file:
        original_local_path = self.get_local_path_from_uuid(resource_uuid)

        dest = os.path.join(staging_dir, os.path.basename(original_local_path))
        copy_local_resource(original_local_path, dest)
        return dest


class LocalDockerSingleDataResourceConverter(LocalDataResourceConverter):
    '''
    This converter takes a DataResource instance (for a single file,
    which is simply a UUID) and returns the path to 
    the local file located in a sandbox dir.

    This converter takes that UUID, finds the Resource/file, brings it local, and returns
    the local path.
    '''
    def convert(self, input_key, user_input, op_dir, staging_dir):
        '''
        user_input is the dictionary-representation of a api.data_structures.UserOperationInput
        '''
        resource_uuid = user_input
        dest = self.copy_local_resource_to_staging(resource_uuid, staging_dir)
        return {input_key: dest}


class LocalDockerSingleDataResourceWithTypeConverter(LocalDataResourceConverter):
    '''
    This converter takes a DataResource instance (for a single file,
    which is simply a UUID) and returns a delimited string which includes
    the path and the resource type

    This converter takes that UUID, finds the Resource/file, brings it local, and returns
    the local path concatenated with the resource type.

    This converter saves us from having to define additional input fields for certain ops. 
    As an example:
    consider an operation where we can take in a type of matrix (e.g. MTX, EXP_MTX, etc.)
    and subset it (by rows or cols). 
    To output a resource of the same type, we need to know the input type.
    We don't need to solicit that input from the user since we already have it in our db.
    '''

    # This is the delimiter we use to separate the path from the resource type
    DELIMITER = ':::'

    def convert(self, input_key, user_input, op_dir, staging_dir):
        '''
        user_input is the dictionary-representation of a api.data_structures.UserOperationInput
        '''
        resource_uuid = user_input
        resource = self.get_resource(resource_uuid)
        resource_type = resource.resource_type
        dest = self.copy_local_resource_to_staging(resource_uuid, staging_dir)
        formatted_str = '{p}{delim}{rt}'.format(
            p = dest,
            rt = resource_type,
            delim = LocalDockerSingleDataResourceWithTypeConverter.DELIMITER
        )
        return {input_key: formatted_str}

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

    This converter takes the list UUIDs, finds each Resource/file, brings it local,
    copies to a staging dir and returns a list of paths to those copies.
    '''

    def get_path_list(self, user_input, staging_dir):
        path_list = []
        if type(user_input) == list:
            for u in user_input:
                path_list.append(self.copy_local_resource_to_staging(u, staging_dir))
        elif type(user_input) == str:
            path_list.append(self.copy_local_resource_to_staging(user_input, staging_dir))
        else:
            logger.error('Unrecognized type submitted for DataResource value: {v}'.format(
                v = value
            ))
        return path_list

    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self.get_path_list(user_input, staging_dir)
        return {input_key: self.to_string(path_list)}

class LocalDockerCsvResourceConverter(LocalDockerMultipleDataResourceConverter, CsvMixin):
    pass


class LocalDockerSpaceDelimResourceConverter(LocalDockerMultipleDataResourceConverter, SpaceDelimMixin):
    pass


class CromwellSingleDataResourceConverter(BaseDataResourceConverter):
    '''
    This converter takes a DataResource instance (for a single file,
    which is simply a UUID) and returns the path to 
    the file in cloud storage.

    Note that if Cromwell is enabled, we do not allow local storage, so we do not 
    need to handle cases where we might have to push a local file into cloud-based 
    storage.
    '''

    def convert(self, input_key, user_input, op_dir, staging_dir):
        resource_uuid = user_input
        r = self.get_resource(resource_uuid)
        return {input_key: r.path}

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

    def get_path_list(self, user_input):
        path_list = []
        if type(user_input) == list:
            for u in user_input:
                r = self.get_resource(u)
                path_list.append(r.path)
        elif type(user_input) == str:
            r = self.get_resource(user_input)
            path_list.append(r.path)
        else:
            logger.error('Unrecognized type submitted for DataResource value: {v}'.format(
                v = value
            ))
        return path_list

    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self.get_path_list(user_input)
        return {input_key: self.to_string(path_list)}

class CromwellCsvResourceConverter(CromwellMultipleDataResourceConverter, CsvMixin):
    pass


class CromwellSpaceDelimResourceConverter(CromwellMultipleDataResourceConverter, SpaceDelimMixin):
    pass