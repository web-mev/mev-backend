from api.runners.base import OperationRunner


class RemoteCromwellRunner(OperationRunner):
    '''
    Class that handles execution of `Operation`s using the WDL/Cromwell
    framework
    '''
    MODE = 'cromwell'