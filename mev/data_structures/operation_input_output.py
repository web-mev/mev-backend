import logging

from exceptions import DataStructureValidationException, \
    AttributeValueError

from data_structures.operation_input_spec import InputSpec

logger = logging.getLogger(__name__)

class OperationInputOutput(object):
    '''
    This class defines a general data structure that holds information about
    inputs or outputs to an analysis `Operation`.

    Structured as:
    ```
    {
        "description":"...",
        "name":"...",
        "required": <boolean>,
        "converter": "...",
        "spec": {
            "attribute_type": "DataResource", 
            "resource_type": "FT", 
            "many": false
        }
    }
    ```
    Note that `spec` is itself a type (`InputSpec`/`OutputSpec`) we define
    and validate elsewhere.

    The required keys for BOTH inputs and outputs are defined here. Add to them
    if you need more in the implementing type
    '''

    IS_REQUIRED_KEY = 'required'
    CONVERTER_KEY = 'converter'
    SPEC_KEY = 'spec'
    REQUIRED_KEYS = set([
        IS_REQUIRED_KEY,
        CONVERTER_KEY,
        SPEC_KEY
    ])

    def __init__(self, submitted_dict):
        '''
        `submitted_dict` is a dictionary. In this constructor,
        we check for the required fields and assign the members.
        '''
        if not type(submitted_dict) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' input expects a dictionary.')

        self._check_keys(submitted_dict.keys())
        # at this point all the required keys should be there.

        # whether the input field is actually required.
        # Cast this as a boolean AFTER casting as int
        # This allows, 0,"0",False (and the True equivalents)
        # but rejects strings that can't be cast to int.
        try:
            self.required = bool(int(submitted_dict[self.IS_REQUIRED_KEY]))
        except ValueError as ex:
            raise AttributeValueError('The "required" key should'
                ' be specified using standard boolean values.')

        # how to convert a user-supplied input to something
        # that the particular operation runner can use. For instance,
        # the input might be a UUID referencing a file. For our docker
        # runner, we need a local filepath. The converter (given as a
        # python "dot string") does that translation/conversion.
        # We do NOT check that the particular string is valid here, however.
        self.converter = str(submitted_dict[self.CONVERTER_KEY])

        # a nested object which describes the input itself (e.g. 
        # a number, a string, a file). Of type `InputSpec`
        self.spec = self.spec_type(submitted_dict[self.SPEC_KEY])
        
    def _check_keys(self, keys):
        submitted_keys = set(keys)
        missing_keys = self.REQUIRED_KEYS.difference(submitted_keys)
        extra_keys = submitted_keys.difference(self.REQUIRED_KEYS)
        if missing_keys:
            raise DataStructureValidationException('Missing the following'
                f' keys in the input: {",".join(missing_keys)}')
        elif extra_keys:
            raise DataStructureValidationException('The input contained'
                f' invalid extra keys: {",".join(extra_keys)}')

    def to_dict(self):
        d = {}
        d[self.IS_REQUIRED_KEY] = self.required
        d[self.CONVERTER_KEY] = self.converter
        d[self.SPEC_KEY] = self.spec.to_dict()
        return d

    def __eq__(self, other):
        a = self.spec == other.spec
        b = self.description == other.description
        c = self.name == other.name
        d = self.converter == other.converter
        e = self.required == other.required
        return all([a,b,c,d,e])

    def __repr__(self):
        return f'{self.typename} ({self.name}).\n Spec:\n{self.spec}'