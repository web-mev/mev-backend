import logging

from .local_docker import LocalDockerRunner
from .remote_cromwell import RemoteCromwellRunner

logger = logging.getLogger(__name__)

RUNNER_MAPPING = {
    LocalDockerRunner.NAME: LocalDockerRunner,
    RemoteCromwellRunner.NAME: RemoteCromwellRunner
}
AVAILABLE_RUNNERS = list(RUNNER_MAPPING.keys())


def get_runner(run_mode):
    '''
    Given the run mode (as given in an operation spec),
    return the class that implements that job running method.
    '''
    try:
        return RUNNER_MAPPING[run_mode]
    except KeyError as ex:
        logger.error(f'Requested an unknown run mode: {run_mode}')
        raise ex
 

def submit_job(executed_op, op, validated_inputs):
    '''
    Submits the job to the proper runner.

    `executed_op` is an instance of ExecutedOperation (database model)
    `op` is an instance of data_structures.operation.Operation
    `validated_inputs` is a dict of inputs. Each key matches a key 
      from the `op_data` and the value is an instance of `UserOperationInput`
    '''
    runner_class = get_runner(executed_op.mode)
    runner = runner_class()
    runner.run(executed_op, op, validated_inputs)


def finalize_job(executed_op, op):
    '''
    Finalizes the job using the proper runner.

    `executed_op` is an instance of ExecutedOperation (database model)
    `op` is an instance of data_structures.operation.Operation
    '''
    runner_class = get_runner(executed_op.mode)
    runner = runner_class()
    runner.finalize(executed_op, op)