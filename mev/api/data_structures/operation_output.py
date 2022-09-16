import logging


logger = logging.getLogger(__name__)

class OperationOutput(object):
    '''
    This class defines a general data structure that holds information about
    outputs from an analysis (`Operation`)
    '''

    def __init__(self, spec, converter, required):

        # whether the output field is actually required
        self.required = required

        # how to convert a job output to something
        # that webmev can understand. For instance,
        # the output might be a path in a bucket. We need to
        # convert that to a Resource in a user's workspace. 
        # The converter (given as a python "dot string") 
        # does that translation/conversion
        self.converter = converter

        # a nested object which describes the output itself (e.g. 
        # a number, a string, a file). Of type `OutputSpec`
        self.spec = spec

    def to_dict(self):
        d = {}
        d['required'] = self.required
        d['converter'] = self.converter
        d['spec'] = self.spec.to_dict()
        return d

    def __eq__(self, other):
        a = self.spec == other.spec
        b = self.required == other.required
        c = self.converter == other.converter
        return all([a,b,c])

    def __repr__(self):
        return 'OperationOutput.\n Spec:\n{spec}'.format(
            spec=self.spec,
        )