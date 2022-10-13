import logging

from api.models import WorkspaceExecutedOperation
from api.utilities.operations import get_operation_instance_data
from data_structures.data_resource_attributes import get_all_data_resource_typenames

logger = logging.getLogger(__name__)


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
            if spec['attribute_type'] in get_all_data_resource_typenames():
                if spec['many']:
                    assert(type(v) is list)
                    resource_uuids.extend(v)
                else:
                    assert(type(v) is str)
                    resource_uuids.append(v)
    return resource_uuids


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
    for exec_op in workspace_executed_ops:
        if exec_op.job_failed:
            logger.info('Skipping inspection of job ({u}) since it failed.'.format(u = str(exec_op.pk)))
            continue
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
