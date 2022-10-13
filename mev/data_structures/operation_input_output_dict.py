import logging

from exceptions import WebMeVException, \
    DataStructureValidationException

from data_structures.operation_input import OperationInput
from data_structures.operation_output import OperationOutput

logger = logging.getLogger(__name__)


class OperationInputOutputDict(object):
    '''
    This class wraps a native dictionary and collects all the inputs
    or outputs of an Operation.

    Basically a mapping of unique keys to OperationInput/OperationOuput objects.
    '''

    def __init__(self, submitted_dict):
        if not type(submitted_dict) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' input expects a dictionary.')  

        d = {}
        for k,v in submitted_dict.items():
            try:
                d[k] = self.input_type(v)
            except WebMeVException as ex:
                message = f'Problem with input key "{k}". {ex}'
                # This raises the original type, but with additional
                # info to make fixing the issue easier.
                raise type(ex)(message)
        self._value = d

    def to_dict(self):
        m = {}
        for k,v in self._value.items():
            m[k] = v.to_dict()
        return m

    def keys(self):
        return self._value.keys()

    def __getitem__(self, key):
        return self._value[key]

    def __eq__(self, other):
        # first check they have the same set of keys
        if not (self._value.keys() == other._value.keys()):
            return False

        # now dive-in and look at the individual dicts
        equal_vals_list = []
        for key, val in self._value.items():
            other_val = other._value[key]
            equal_vals_list.append(val == other_val)
        return all(equal_vals_list)


class OperationInputDict(OperationInputOutputDict):
    input_type = OperationInput
    def __repr__(self):
        return 'OperationInputDict with keys: {k}'.format(
            k = ', '.join(self._value.keys())
        )


class OperationOutputDict(OperationInputOutputDict):
    input_type = OperationOutput
    def __repr__(self):
        return 'OperationOutputDict with keys: {k}'.format(
            k = ', '.join(self._value.keys())
        )