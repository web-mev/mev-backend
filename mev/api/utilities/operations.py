import os
import json
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.utilities.basic_utils import read_local_file
from api.data_structures import create_attribute
from api.data_structures.attributes import DataResourceAttribute
from api.data_structures.user_operation_input import user_operation_input_mapping

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

def validate_operation(operation_dict):
    '''
    Takes a dictionary and validates it against the definition
    of an `Operation`. Returns an instance of an `OperationSerializer`.
    '''
    logger.info('Validate the dictionary against the definition'
    ' of an Operation...: {d}'.format(d=operation_dict))
    from api.serializers.operation import OperationSerializer
    op_serializer = OperationSerializer(data=operation_dict)
    op_serializer.is_valid(raise_exception=True)
    logger.info('Operation specification was valid.')
    return op_serializer

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

        # seems roundabout, but then feed that Operation back into the 
        # serializer so we can get the serialized representation via the
        # `data` property
        from api.serializers.operation import OperationSerializer
        s = OperationSerializer(op_data_structure)
        return s.data
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
                supplied_input = spec['default']
            else:
                supplied_input = None

        # now validate that supplied input against the spec
        attribute_typename = spec['attribute_type']
        try:
            user_operation_input_class = user_operation_input_mapping[attribute_typename]
            logger.info(user_operation_input_class)
        except KeyError as ex:
            logger.error('Could not find an appropriate class for handling the user input'
                ' for the typename of {t}'.format(
                    t=attribute_typename
                )
            )
        if supplied_input:
            final_inputs[key] = user_operation_input_class(user, workspace, key, supplied_input, spec)
        else:
            final_inputs[key] = None
    return final_inputs

def collect_resource_uuids(op_input_or_output, exec_op_input_or_output):
    '''
    This function goes through the inputs or outputs of an ExecutedOperation
    to return a set of resource UUIDs that were "used" either as an input
    or an output.

    op_input_or_output: the dict of inputs/outputs for an Operation. This comes
      from parsing the operation specification file.
    exec_op_input_or_output: the dict of actual inputs or outputs created or used
      in the course of executing an operation.
    '''
    resource_uuids = []
    for k,v in exec_op_input_or_output.items():
        # k is the 'key' of the output, v is the actual value assigned
        if not k in op_input_or_output:
            logger.error('The key "{k}" was NOT in the operation inputs/outputs.'
                ' Expected keys: {keys}'.format(
                    k=k,
                    keys = ', '.join(op_input_or_output.keys())
                )
            )
            raise Exception('Discrepancy between the ExecutedOperation and the Operation'
                ' it was based on. Should NOT happen!'
            )
        else:
            # the key existed in the Operation (as it should). Get the spec dictating
            spec = op_input_or_output[k]['spec']
            if spec['attribute_type'] == DataResourceAttribute.typename:
                if spec['many']:
                    assert(type(v) is list)
                    resource_uuids.extend(v)
                else:
                    assert(type(v) is str)
                    resource_uuids.append(v)
    return resource_uuids
