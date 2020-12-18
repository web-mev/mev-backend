import logging

logger = logging.getLogger(__name__)

class OperationInputOutputDict(object):
    '''
    This class wraps a native dictionary and collects all the inputs
    or outputs of an Operation.

    Basically a mapping of unique keys to OperationInput/OperationOuput objects.
    '''

    def __init__(self, d):
        self.d = d
        
    def to_dict(self):
        m = {}
        for k,v in self.d.items():
            m[k] = v.to_dict()
        return m

    def __getitem__(self, key):
        return self.d[key]

    def __eq__(self, other):
        # first check they have the same set of keys
        if not (self.d.keys() == other.d.keys()):
            return False

        # now dive-in and look at the individual dicts
        equal_vals_list = []
        for key, val in self.d.items():
            other_val = other.d[key]
            equal_vals_list.append(val == other_val)
        return all(equal_vals_list)

class OperationInputDict(OperationInputOutputDict):
    
    def __repr__(self):
        return 'OperationInputDict with keys: {k}'.format(
            k = ', '.join(self.d.keys())
        )


class OperationOutputDict(OperationInputOutputDict):
    
    def __repr__(self):
        return 'OperationOutputDict with keys: {k}'.format(
            k = ', '.join(self.d.keys())
        )