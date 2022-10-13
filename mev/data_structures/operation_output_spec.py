import logging

from data_structures.operation_input_and_output_spec import InputOutputSpec

logger = logging.getLogger(__name__)


class OutputSpec(InputOutputSpec):
    '''
    Specialization of InputOutputSpec that dictates
    behavior specific for outputs. Use this for overrides
    as required.
    '''
    def __init__(self, spec_dict):
        super().__init__(spec_dict)