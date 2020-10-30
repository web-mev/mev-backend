import logging

from .local_docker import LocalDockerRunner
from .remote_cromwell import RemoteCromwellRunner
from api.utilities.operations import get_operation_instance_data

logger = logging.getLogger(__name__)

AVAILABLE_RUN_MODES = [
    LocalDockerRunner.MODE,
    RemoteCromwellRunner.MODE
]

RUNNER_MODE_MAPPING = {
    LocalDockerRunner.MODE: LocalDockerRunner,
    RemoteCromwellRunner.MODE: RemoteCromwellRunner
}

RUNNER_NAME_MAPPING = {
    LocalDockerRunner.NAME: LocalDockerRunner,
    RemoteCromwellRunner.NAME: RemoteCromwellRunner
}

def get_runner(mode=None, name=None):
    '''
    Given either the mode (as given in an operation spec) or by name,
    return the class that implements that job running method.
    '''
    if mode:
        try:
            return RUNNER_MODE_MAPPING[mode]
        except KeyError as ex:
            logger.error('Requested an unknown run mode: {mode}'.format(
                mode=mode
            ))
            raise ex
    if name:
        try:
            return RUNNER_NAME_MAPPING[name]
        except KeyError as ex:
            logger.error('Requested an unknown runner name: {name}'.format(
                name=name
            ))
            raise ex
    else:
        logger.error('Need to get the job runner by name or mode. Received neither.')
        raise Exception('The get_runner function needs either a name or a mode.')
 
def submit_job(executed_op, op_data, validated_inputs):
    '''
    Submits the job to the proper runner.

    `executed_op` is an instance of ExecutedOperation (database model)
    `op_data` is a dict parsed from an `Operation` spec (data structure, NOT db model)
    `validated_inputs` is a dict of inputs. Each key matches a key 
      from the `op_data` and the value is an instance of `UserOperationInput`
    '''
    runner_class = get_runner(mode=op_data['mode'])
    runner = runner_class()
    runner.run(executed_op, op_data, validated_inputs)

def finalize_job(executed_op):
    '''
    Finalizes the job using the proper runner.

    `executed_op` is an instance of ExecutedOperation (database model)
    '''
    runner_class = get_runner(executed_op.mode)
    runner = runner_class()
    runner.finalize(executed_op)