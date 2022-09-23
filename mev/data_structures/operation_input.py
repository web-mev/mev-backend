import logging

logger = logging.getLogger(__name__)

class OperationInput(object):
    '''
    This class defines a general data structure that holds information about
    inputs to an analysis (`Operation`)
    '''

    def __init__(self, description, name, spec, converter, required):

        # a descriptive field to help users
        self.description = description

        # the label of the field in the UI
        self.name = name

        # whether the input field is actually required
        self.required = required

        # how to convert a user-supplied input to something
        # that the particular operation runner can use. For instance,
        # the input might be a UUID referencing a file. For our docker
        # runner, we need a local filepath. The converter (given as a
        # python "dot string") does that translation/conversion
        self.converter = converter

        # a nested object which describes the input itself (e.g. 
        # a number, a string, a file). Of type `InputSpec`
        self.spec = spec
        
    def to_dict(self):
        d = {}
        d['description'] = self.description
        d['name'] = self.name
        d['required'] = self.required
        d['converter'] = self.converter
        d['spec'] = self.spec.to_dict()
        return d

    def __eq__(self, other):
        a = self.spec == other.spec
        b = self.description == other.description
        c = self.name == other.name
        d = self.converter == other.converter
        e = self.required == other.required
        return all([a,b,c,d,e])

    def __repr__(self):
        return 'OperationInput ({name}).\n Spec:\n{spec}'.format(
            spec=self.spec,
            name=self.name
        )