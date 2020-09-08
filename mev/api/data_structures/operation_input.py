import logging

logger = logging.getLogger(__name__)

class OperationInput(object):
    '''
    This class defines a general data structure that holds information about
    inputs to an analysis (`Operation`)
    '''

    def __init__(self, description, name, spec, required=False):

        # a descriptive field to help users
        self.description = description

        # the label of the field in the UI
        self.name = name

        # whether the input field is actually required
        self.required = required

        # a nested object which describes the input itself (e.g. 
        # a number, a string, a file). Of type `InputSpec`
        self.spec = spec
        
    def to_dict(self):
        d = {}
        d['description'] = self.description
        d['name'] = self.name
        d['required'] = self.required
        d['spec'] = self.spec.to_dict()
        return d

    def __eq__(self, other):
        a = self.spec == other.spec
        b = self.description == other.description
        c = self.name == other.name
        d = self.required == other.required
        return all([a,b,c,d])

    def __repr__(self):
        return 'OperationInput ({name}).\n Spec:\n{spec}'.format(
            spec=self.spec,
            name=self.name
        )