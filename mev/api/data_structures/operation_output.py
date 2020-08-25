import logging


logger = logging.getLogger(__name__)

class OperationOutput(object):
    '''
    This class defines a general data structure that holds information about
    outputs from an analysis (`Operation`)
    '''

    def __init__(self, spec):

        # a nested object which describes the output itself (e.g. 
        # a number, a string, a file). Of type `OutputSpec`
        self.spec = spec


    def __eq__(self, other):
        return self.spec == other.spec