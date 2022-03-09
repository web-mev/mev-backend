import logging


logger = logging.getLogger(__name__)

class OperationOutput(object):
    '''
    This class defines a general data structure that holds information about
    outputs from an analysis (`Operation`)
    '''

    def __init__(self, spec, required = True):

        # whether the output field is actually required
        self.required = required

        # a nested object which describes the output itself (e.g. 
        # a number, a string, a file). Of type `OutputSpec`
        self.spec = spec

    def to_dict(self):
        d = {}
        d['required'] = self.required
        d['spec'] = self.spec.to_dict()
        return d

    def __eq__(self, other):
        a = self.spec == other.spec
        b = self.required == other.required
        return all([a,b])

    def __repr__(self):
        return 'OperationOutput.\n Spec:\n{spec}'.format(
            spec=self.spec,
        )