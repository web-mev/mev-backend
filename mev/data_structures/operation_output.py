import logging

from data_structures.operation_output_spec import OutputSpec
from data_structures.operation_input_output import OperationInputOutput

logger = logging.getLogger(__name__)


class OperationOutput(OperationInputOutput):
    '''
    This class extends the OperationInputOutput type
    to dictate the nested type of `spec`.

    Additionally, if more fields are required, you 
    can add to the REQUIRED_KEYS class member
    '''
    typename = 'OperationOutput'
    spec_type = OutputSpec

    def __repr__(self):
        return f'{self.typename}\n Spec:\n{self.spec}'