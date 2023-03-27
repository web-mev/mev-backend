from copy import deepcopy

from exceptions import NullAttributeError, \
    AttributeValueError

    
class BaseAttributeType(object):
    '''
    This is a base class for all the types of attributes we might
    implement. It contains common operations/logic. 
    '''

    def __init__(self, val, **kwargs):

        # do we allow null/NaN? If not explicitly given,
        # assume we do NOT allow nulls
        try:
            self._allow_null = bool(kwargs.pop('allow_null'))
        except KeyError:
            self._allow_null = False

        # do we allow extra keys (which are ultimately ignored)? 
        # If not explicitly given, weassume we do NOT allow extras. 
        # This makes checking very strict.
        try:
            self._ignore_extra_keys = bool(kwargs.pop('ignore_extra_keys'))
        except KeyError:
            self._ignore_extra_keys = False

        # since we will often pop items out of `val`, we 
        # copy it so we don't generate side effects.
        val_copy = deepcopy(val)

        # Kickoff any validation via the setter
        self.value = val_copy

        # if kwargs is not an empty dict, raise an exception.
        # The derived classes should pop off the kwargs specific
        # to their implementation
        if kwargs != {}:
            raise AttributeValueError('This type of attribute does not '
                                      ' accept additional keyword arguments.'
                                      f' Received: {",".join(kwargs.keys())}')

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        '''
        This setter method will ultimately call a _value_validator method,
        so override that method to implement custom validation logic.
        '''
        if val is None:
            if not self._allow_null:
                raise NullAttributeError('Cannot set the value to None unless'
                                         ' passing "allow_null=True"')
            self._value = None
        else:
            self._value_validator(val)

    def _value_validator(self, val):
        '''
        This method is where we perform custom logic for setting the _value
        attribute. Override in your subclass
        '''
        self._value = val

    def to_dict(self):
        '''
        Returns a dictionary representation appropriate for use in JSON-like
        responses.

        Override as required in your subclass.
        '''
        return {
            'attribute_type': self.typename,
            'value': self.value
        }

    def __eq__(self, other):
        same_type = self.typename == other.typename
        same_val = self.value == other.value
        return all([same_type, same_val])

    def __repr__(self):
        return f'{self.typename}: {self.value}'

    def __str__(self):
        return f'{self.value}'