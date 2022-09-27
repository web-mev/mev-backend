import os
import json
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.utilities.basic_utils import read_local_file

from api.serializers.operation import OperationSerializer

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
                path = filepath,
                ex = ex
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
        namelist, pathlist = [],[]
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
    of an `Operation`. Returns an instance of an `OperationSerializer`.
    '''
    logger.info('Validate the dictionary against the definition'
    ' of an Operation...: {d}'.format(d=operation_dict))
    #from api.serializers.operation import OperationSerializer
    op_serializer = OperationSerializer(data=operation_dict)
    try:
        op_serializer.is_valid(raise_exception=True)
    except Exception as ex:
        raise ex
    logger.info('Operation specification was valid.')
    return op_serializer

def get_operation_data_list(uuid_list):
    '''
    Return a list of Operation instances (in serialized json format)
    given a list of UUIDs. Does not check the existence of those UUIDs
    for addressing Operation instances. That should be done prior.
    '''
    pass

def get_operation_instance_data(operation_db_model):
    '''
    Using an Operation (database model) instance, return the
    Operation instance (the data structure)
    '''

    f = os.path.join(
        settings.OPERATION_LIBRARY_DIR, 
        str(operation_db_model.id), 
        settings.OPERATION_SPEC_FILENAME
    )
    if os.path.exists(f):
        j = read_operation_json(f)
        op_serializer = validate_operation(j)

        # get an instance of the data structure corresponding to an Operation
        op_data_structure = op_serializer.get_instance()
        return op_data_structure.to_dict()
    else:
        logger.error('Integrity error: the queried Operation with'
            ' id={uuid} did not have a corresponding folder.'.format(
                uuid=str(operation_db_model.id)
            )
        )
        return None

def validate_operation_inputs(user, inputs, operation, workspace):
    '''
    This function validates the inputs to check that they are compatible
    with the Operation that a user wishes to run.

    `user` is the user (database object) requesting the executed Operation
    `inputs` is a dictionary of input parameters for the Operation
    `operation` is an instance of Operation (the database model)
    `workspace` is an instance of Workspace (database model)

    Note that `workspace` is not required, as some operations can be run
    outside the context of a workspace. In that instance, `workspace`
    should be explicitly set to None
    '''
    # get the Operation data structure given the operation database instance:
    operation_spec_dict = get_operation_instance_data(operation)

    final_inputs = {}
    for key, op_input in operation_spec_dict['inputs'].items():
        required = op_input['required']
        spec = op_input['spec']
        key_is_present = key in inputs.keys()

        if key_is_present:
            supplied_input = inputs[key]
        elif required: # key not there, but it is required
            logger.info('The key ({key}) was not among the inputs, but it'
                ' is required.'.format(key=key)
            )
            raise ValidationError({key: 'This is a required input field.'})
        else: # key not there, but NOT required
            logger.info('key was not there, but also NOT required.')
            if 'default' in spec: # is there a default to use?
                logger.info('There was a default value in the operation spec. Since no value was given, use that.')
                supplied_input = spec['default']
            else:
                supplied_input = None

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
                    x = key,
                    t = attribute_typename
                )
            )
        if supplied_input is not None:
            logger.info('Check supplied input: {d}'.format(d=supplied_input))
            final_inputs[key] = submitted_input_class(user, operation, workspace, key, supplied_input, spec)
        else:
            final_inputs[key] = None
    return final_inputs