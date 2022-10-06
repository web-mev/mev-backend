import os
import json
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from exceptions import WebMeVException, \
    ExecutedOperationInputOutputException

from api.utilities.basic_utils import read_local_file
from api.utilities.resource_utilities import check_resource_request_validity

from data_structures.operation import Operation

logger = logging.getLogger(__name__)


def read_operation_json(filepath):
    '''
    Performs ingestion of a JSON-format file defining an `Operation`

    Accepts a local filepath for the JSON file, returns a dict
    '''
    try:
        logger.info('Parse Operation definition file at {path}'.format(
            path=filepath
        ))
        fp = read_local_file(filepath)
        j = json.load(fp)
        fp.close()
        logger.info('Done reading file.')
        return j
    except Exception as ex:
        logger.error('Could not read the operation JSON-format file at {path}.'
                     ' Exception was {ex}'.format(
                         path=filepath,
                         ex=ex
                     )
                     )


def resource_operations_file_is_valid(operation_resource_dict, necessary_keys):
    '''
    Some Operations have "static" resources that are user-independent. The 
    repository can contain a file which provides paths to these OperationDataResources
    and here we check that the data structure is formatted correctly and that
    it has the proper keys
    '''
    # require strict equality-- don't want to have extra keys in the
    # operation_resource_dict. Don't allow sloppy specs.
    if not (operation_resource_dict.keys() == necessary_keys):
        return False

    for k in necessary_keys:
        l = operation_resource_dict[k]
        if not type(l) is list:
            return False
        namelist, pathlist = [], []
        for item in l:
            if not type(item) is dict:
                return False
            if not (item.keys() == set(['name', 'path', 'resource_type'])):
                return False
            namelist.append(item['name'])
            pathlist.append(item['path'])

        # ensure the names and paths are unique for the "options"
        # corresponding to this input
        if len(set(namelist)) < len(namelist):
            return False
        if len(set(pathlist)) < len(pathlist):
            return False
    return True


def validate_operation(operation_dict):
    '''
    Takes a dictionary and validates it against the definition
    of an `Operation`. Returns an instance of 
    data_structures.operation.Operation
    '''
    logger.info('Validate the dictionary against the definition'
                f' of an Operation...: {operation_dict}')

    try:
        return Operation(operation_dict)
    except WebMeVException as ex:
        logger.info('Failed to validate the operation dict.'
                    f' The exception was: {ex}\n'
                    f' The data was: {operation_dict}')
        raise ex
    except Exception as ex:
        logger.info('Unexpected exception when validating the operation dict.'
                    f' The exception was: {ex}\n'
                    f' The data was: {operation_dict}')
        raise ex


def get_operation_data_list(uuid_list):
    '''
    Return a list of Operation instances (in serialized json format)
    given a list of UUIDs. Does not check the existence of those UUIDs
    for addressing Operation instances. That should be done prior.
    '''
    pass

def get_operation_instance(operation_db_model):
    '''
    Using an Operation (database model) instance, return an
    instance of data_structures.operation.Operation
    '''
    f = os.path.join(
        settings.OPERATION_LIBRARY_DIR,
        str(operation_db_model.id),
        settings.OPERATION_SPEC_FILENAME
    )
    if os.path.exists(f):
        j = read_operation_json(f)
        return validate_operation(j)
    else:
        logger.error('Integrity error: the queried Operation with'
                     f' id={operation_db_model.id} did not have a'
                     ' corresponding folder.')
        raise Exception('Missing operation files.')


def get_operation_instance_data(operation_db_model):
    '''
    Using an Operation (database model) instance, return the
    dict representation of data_structures.operation.Operation
    '''
    op = get_operation_instance(operation_db_model)
    return op.to_dict()


def validate_operation_inputs(
        user, user_inputs, operation_db_instance, workspace):
    '''
    This function validates the inputs to check that they are compatible
    with the Operation that a user wishes to run.

    `user` is the user (database object) requesting the executed Operation
    `user_inputs` is a dictionary of input parameters for the Operation
        as submitted by a user
    `operation_db_instance` is an instance of Operation (the database model)
    `workspace` is an instance of Workspace (database model)

    Note that `workspace` is not required, as some operations can be run
    outside the context of a workspace. In that instance, `workspace`
    should be explicitly set to None
    '''
    # get the Operation data structure given the operation database instance:
    operation = get_operation_instance(operation_db_instance)

    final_inputs = {}
    op_inputs = operation.inputs
    for key in op_inputs.keys():
        op_input = op_inputs[key]
        required = op_input.required
        spec = op_input.spec
        key_is_present = key in user_inputs.keys()

        if key_is_present:
            supplied_input = user_inputs[key]
        elif required:  # key not there, but it is required
            logger.info('The key ({key}) was not among the inputs, but it'
                        ' is required.'.format(key=key)
                        )
            raise ValidationError({key: 'This is a required input field.'})
        else:  # key not there, but NOT required
            logger.info('key was not there, but also NOT required.')
            if spec.default is not None:  # is there a default to use?
                logger.info(
                    'There was a default value in the operation spec.' 
                    ' Since no value was given, use that.')
                supplied_input = spec.default
            else:
                supplied_input = None

        # validate the input. Note that for simple inputs
        # this is all we need. However, for inputs like 
        # data resources, we need to perform additional checks (below)
        op_input.check_value(supplied_input)

        if op_input.is_data_resource_input():
            logger.info('Input corresponds to a data resource. Perform'
                ' additional checks.')
            # if we are dealing with a file-type, we need
            # to ensure that:
            # - the file is owned by the requesting user
            # - the file is in the workspace
            # - the file has the proper resource type

            # if this doens't raise an exception, then the user does own
            # the file:
            resource_instance = check_resource_request_validity(
                user, supplied_input)
            if not workspace in resource_instance.workspaces:
                raise ExecutedOperationInputOutputException('The resource'
                    f' ({submitted_input}) was not part of the workspace'
                    ' where the analysis operation was requested.')
            # now need to check the resource type:
            # this gets the instance, e.g. an instance of
            # data_structures.data_resource_attributes.DataResourceAttribute
            op_input.spec.value

        # now validate that supplied input against the spec
        attribute_typename = spec['attribute_type']
        try:
            # TODO: address this- set to None to avoid import
            submitted_input_class = None
            logger.info(submitted_input_class)
        except KeyError as ex:
            logger.error('Could not find an appropriate class for handling the user input'
                         ' for the typename of {t}'.format(
                             t=attribute_typename
                         )
                         )
            raise Exception('Could not find an appropriate class for typename {t} for'
                            ' the input named {x}.'.format(
                                x=key,
                                t=attribute_typename
                            )
                            )
        if supplied_input is not None:
            logger.info('Check supplied input: {d}'.format(d=supplied_input))
            final_inputs[key] = submitted_input_class(
                user, operation, workspace, key, supplied_input, spec)
        else:
            final_inputs[key] = None
    return final_inputs
