import logging

from api.runners.base import OperationRunner

logger = logging.getLogger(__name__)
class LocalDockerRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using Docker on the local
    machine
    '''
    MODE = 'local_docker'

    def run(self, executed_op, op_data, validated_inputs):
        logger.info('Running in local Docker mode.')
        logger.info('Executed op:', (executed_op.id))
        logger.info('Op data:', op_data)
        logger.info(validated_inputs)
        