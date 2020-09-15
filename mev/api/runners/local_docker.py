import logging

from api.runners.base import OperationRunner
from api.utilities.operations import get_operation_instance_data

logger = logging.getLogger(__name__)
class LocalDockerRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using Docker on the local
    machine
    '''
    MODE = 'local_docker'

    # A list of files that are required to be part of the repository
    REQUIRED_FILES = ['docker/Dockerfile']

    def run(self, executed_op, op, validated_inputs):
        logger.info('Running in local Docker mode.')
        logger.info('Executed op:', (executed_op.id))
        logger.info('Op data:', op_data)
        logger.info(validated_inputs)
        op_data = get_operation_instance_data(op)

        # have to translate the user-submitted inputs to those that
        # the local docker runner can work with.
        # For instance, a differential gene expression requires one to specify
        # the samples that are in each group-- to do this, the Operation requires
        # two ObservationSet instances are submitted as arguments. The "translator"
        # will take the ObservationSet data structures and turn them into something
        # that the call with use- e.g. making a CSV list to submit as one of the args
        # like:
        # docker run <image> run_something.R -a sampleA,sampleB -b sampleC,sampleD
