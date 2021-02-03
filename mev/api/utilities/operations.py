import os
import json
import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError

from api.utilities.basic_utils import read_local_file
from api.data_structures import create_attribute, \
    DataResourceAttribute, \
    SimpleDag, \
    DagNode
from api.utilities.resource_utilities import get_resource_by_pk
from api.data_structures.user_operation_input import user_operation_input_mapping
from api.models import Resource, WorkspaceExecutedOperation

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
    from api.serializers.operation import OperationSerializer
    op_serializer = OperationSerializer(data=operation_dict)
    op_serializer.is_valid(raise_exception=True)
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
            user_operation_input_class = user_operation_input_mapping[attribute_typename]
            logger.info(user_operation_input_class)
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
            final_inputs[key] = user_operation_input_class(user, operation, workspace, key, supplied_input, spec)
        else:
            final_inputs[key] = None
    return final_inputs

def check_for_resource_operations(resource_instance, workspace_instance):
    '''
    To prevent deleting critical resources, we check to see if a
    `Resource` instance has been used for any operations within a
    `Workspace`.  If it has, return True.  Otherwise return False.
    '''
    # need to look through all the executed operations to see if the 
    # resource was used in any of those, either as an input or output
    logger.info('Search within workspace ({w}) to see if resource ({r}) was used.'.format(
        w = str(workspace_instance.pk),
        r = str(resource_instance.pk)
    ))
    workspace_executed_ops = WorkspaceExecutedOperation.objects.filter(workspace=workspace_instance)
    used_resource_uuids = set()
    for exec_op in workspace_executed_ops:
        logger.info('Look in executedOp: {u}'.format(u = str(exec_op.pk)))
        # get the corresponding operation spec:
        op = exec_op.operation
        op_data = get_operation_instance_data(op)

        # the operation spec will tell us what the "types" of each input/output are
        op_inputs = op_data['inputs']
        op_outputs = op_data['outputs']

        # the executed ops will have the actual args used. So, for a DataResource
        # "type", it will be a UUID
        exec_op_inputs = exec_op.inputs
        exec_op_outputs = exec_op.outputs

        if exec_op_inputs is not None:
            # list of dataResources used in the inputs of this executed op:
            logger.info('Compare inputs:\n{x}\nto\n{y}'.format(
                x = op_inputs,
                y = exec_op_inputs
            ))
            s1 = collect_resource_uuids(op_inputs, exec_op_inputs)
            logger.info('Found the following DataResources among'
                ' the inputs: {u}'.format(
                    u = ', '.join(s1)
                ))
            if str(resource_instance.pk) in s1:
                return True
            logger.info('Was not in the inputs. Check the outputs.')
        else:
            logger.info('Inputs to the ExecutedOp were None. Moving on.')
        if exec_op_outputs is not None:
            s2 = collect_resource_uuids(op_outputs, exec_op_outputs)
            logger.info('Found the following DataResources among'
            ' the outputs: {u}'.format(
                u = ', '.join(s2)
            ))
            if str(resource_instance.pk) in s2:
                return True
            logger.info('Was not in the outputs. Done checking ExecutedOp ({u}).'.format(
                u = str(exec_op.pk)
            ))
        else:
            logger.info('Outputs of the ExecutedOp were None. Moving on.')
    
    # if we made it this far and have not returned, then the Resource was
    # not used in any of the ExecutedOps in the Workspace
    return False

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

        # Sometimes an operation can declare an output type of DataResource
        # that is given None as a value. For instance, in a clustering operation,
        # we may only cluster on one of the dimensions. This results in one of the
        # output JSON files being unused and hence set to None. If the value is None,
        # we just move onto the next item.
        if v is None:
            continue

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

def create_workspace_dag(workspace_executed_ops):
    '''
    Returns a DAG representing the resources and operations contained in a workspace

    `workspace_executed_ops` is a set of ExecutedOperation (database model) objects
    '''
    graph = SimpleDag()
    for exec_op in workspace_executed_ops:

        # don't want to show failed jobs
        if exec_op.job_failed:
            continue

        # we need the operation definition to know if any of the inputs
        # were DataResources
        op = exec_op.operation
        op_data = get_operation_instance_data(op)

        # the operation spec will tell us what the "types" of each input/output are
        op_inputs = op_data['inputs']
        op_outputs = op_data['outputs']

        # the executed ops will have the actual args used. So, for a DataResource
        # "type", it will be a UUID
        exec_op_inputs = exec_op.inputs
        exec_op_outputs = exec_op.outputs

        # create a node for the operation
        op_node = DagNode(str(exec_op.pk), DagNode.OP_NODE, node_name = op_data['name'])
        graph.add_node(op_node)

        for k,v in exec_op_inputs.items():
            # compare with the expected type:
            op_input_definition = op_inputs[k]
            op_spec = op_input_definition['spec']
            input_type = op_spec['attribute_type']
            if input_type == DataResourceAttribute.typename:
                r = get_resource_by_pk(v)
                resource_node = graph.get_or_create_node(
                    str(v), 
                    DagNode.DATARESOURCE_NODE, 
                    node_name = r.name)
                op_node.add_parent(resource_node)

        # show the outputs if the operation has completed
        if exec_op.execution_stop_datetime:
            for k,v in exec_op_outputs.items():
                # compare with the expected type:
                op_output_definition = op_outputs[k]
                op_spec = op_output_definition['spec']
                output_type = op_spec['attribute_type']
                if output_type == DataResourceAttribute.typename:
                    if v is not None:
                        r = get_resource_by_pk(v)
                        resource_node = graph.get_or_create_node(
                            str(v), 
                            DagNode.DATARESOURCE_NODE, 
                            node_name = r.name)
                        resource_node.add_parent(op_node)
    return graph.serialize()

