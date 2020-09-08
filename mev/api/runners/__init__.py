import logging

from .local_docker import LocalDockerRunner
from .remote_cromwell import RemoteCromwellRunner
from api.utilities.operations import get_operation_instance_data

logger = logging.getLogger(__name__)

AVAILABLE_RUN_MODES = [
    LocalDockerRunner.MODE,
    RemoteCromwellRunner.MODE
]

RUNNER_MAPPING = {
    LocalDockerRunner.MODE: LocalDockerRunner,
    RemoteCromwellRunner.MODE: RemoteCromwellRunner
}

def get_runner(mode):
    try:
        return RUNNER_MAPPING[mode]
    except KeyError as ex:
        logger.error('Requested an unknown run mode: {mode}'.format(
            mode=mode
        ))
        raise ex

def submit_job(executed_op, op, validated_inputs):
    '''
    Submits the job to the proper runner.

    `executed_op` is an instance of ExecutedOperation (database model)
    `op` is an `Operation` (database model)
    `validated_inputs` is a dict of inputs. Each key matches a key 
      from the `op_data` and the value is an instance of `UserOperationInput`
    '''
    # need to read the Operation definition to get the run mode:
    op_data = get_operation_instance_data(op)
    runner_class = get_runner(op_data['mode'])
    runner = runner_class()
    runner.run(executed_op, op_data, validated_inputs)
