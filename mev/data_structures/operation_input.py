import logging

from data_structures.operation_input_spec import InputSpec
from data_structures.operation_input_output import OperationInputOutput

logger = logging.getLogger(__name__)


class OperationInput(OperationInputOutput):
    '''
    This class extends the OperationInputOutput type
    to add a couple more required keys and to dictate the 
    nested type of `spec`.

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
    Note that `spec` is itself a type (`InputSpec`) we define
    and validate elsewhere.
    '''
    typename = 'OperationInput'

    DESCRIPTION_KEY = 'description'
    NAME_KEY = 'name'
    REQUIRED_KEYS = OperationInputOutput.REQUIRED_KEYS.union([
        DESCRIPTION_KEY,
        NAME_KEY
    ])
    
    spec_type = InputSpec

    def __init__(self, submitted_dict):

        super().__init__(submitted_dict)

        # A helpful description for the input
        self.description = str(submitted_dict[self.DESCRIPTION_KEY])

        # the label of the field in the UI
        self.name = str(submitted_dict[self.NAME_KEY])

    def to_dict(self):
        d = super().to_dict()
        d[self.DESCRIPTION_KEY] = self.description
        d[self.NAME_KEY] = self.name
        return d

    def __eq__(self, other):
        base_objects_equal = super().__eq__(other)
        b = self.description == other.description
        c = self.name == other.name
        return all([base_objects_equal,b,c])

    def __repr__(self):
        return f'{self.typename} ({self.name}).\n Spec:\n{self.spec}'