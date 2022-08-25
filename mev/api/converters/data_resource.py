from lib2to3.pytree import convert
import os
import uuid
import logging

from django.core.files.storage import default_storage

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
    This class holds actions/behavior for local-based Resources/files.
    Note that "local" doesn't mean our storage system. Rather, it means
    that we need the file/resource local so that Docker can use it.
    '''

    def _copy_resource_to_staging(self, resource_uuid, staging_dir):
        '''
        Takes a resource UUID and copies the associated file to `staging_dir`
        Returns a path to the copied file
        '''
        resource_instance = self.get_resource(resource_uuid)
        return localize_resource(resource_instance, staging_dir)


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
        dest = self._copy_resource_to_staging(resource_uuid, staging_dir)
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
        dest = self._copy_resource_to_staging(resource_uuid, staging_dir)
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

    def _get_path_list(self, user_input, staging_dir):
        path_list = []
        if type(user_input) == list:
            for u in user_input:
                path_list.append(self._copy_resource_to_staging(u, staging_dir))
        elif type(user_input) == str:
            path_list.append(self._copy_resource_to_staging(user_input, staging_dir))
        else:
            logger.error('Unrecognized type submitted for DataResource value: {v}'.format(
                v = user_input
            ))
        return path_list

    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: path_list}


class LocalDockerCsvResourceConverter(LocalDockerMultipleDataResourceConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: self.to_string(path_list)}

class LocalDockerSpaceDelimResourceConverter(LocalDockerMultipleDataResourceConverter, SpaceDelimMixin):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: self.to_string(path_list)}

class CromwellDataResourceConverter(BaseDataResourceConverter):
    '''
    Contains common behavior for DataResource conversion related to
    the Cromwell runner.

    Use one of the derived classes.
    '''

    def _convert_single_resource(self, resource_uuid, staging_dir):
        '''
        Handles the conversion of a UUID referencing an instance that
        is a child of api.models.AbstractResource and copies to a 
        staging directory in a Cromwell-accessible bucket.

        Returns the full path to the copied file, e.g.
        s3://<cromwell bucket>/<execution UUID>/<file UUID>

        Note that we don't preserve any file names- we just 
        copy to a file named by UUID
        '''
        r = self.get_resource(resource_uuid)
        # the staging_dir is where we copy non-data files (e.g. WDL)
        # and it's local to the server. We also use that UUID to locate
        # files inside a 'directory' in our Cromwell bucket.
        # TODO: move this to settings.
        cromwell_bucket = os.environ['CROMWELL_BUCKET']
        #TODO: is this appropriate here? should we move this to resource utils?
        return default_storage.copy_out_to_bucket(
            r,
            cromwell_bucket,
            os.path.join(
                os.path.basename(staging_dir),
                str(uuid.uuid4())
            )
        )

class CromwellSingleDataResourceConverter(CromwellDataResourceConverter):
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
        path = self._convert_single_resource(resource_uuid, staging_dir)
        return {input_key: path}


class CromwellMultipleDataResourceConverter(CromwellDataResourceConverter):
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

    def _get_path_list(self, user_input, staging_dir):
        path_list = []
        if type(user_input) == list:
            for u in user_input:
                path_list.append(
                    self._convert_single_resource(u, staging_dir)
                )
        elif type(user_input) == str:
            # technically COULD HAVE been multiple resources, but only a single
            # was provided (hence, a single string, not a list)
            path_list.append(
                self._convert_single_resource(user_input, staging_dir)
            )
        else:
            logger.error('Unrecognized type submitted for DataResource value: {v}'.format(
                v = user_input
            ))
        return path_list

    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: path_list}


class CromwellCsvResourceConverter(CromwellMultipleDataResourceConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: self.to_string(path_list)}


class CromwellSpaceDelimResourceConverter(CromwellMultipleDataResourceConverter, SpaceDelimMixin):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        path_list = self._get_path_list(user_input, staging_dir)
        return {input_key: self.to_string(path_list)}