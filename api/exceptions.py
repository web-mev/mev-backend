from rest_framework.exceptions import ValidationError


class StringIdentifierException(ValidationError):
    '''
    Raised if a String identifier (e.g. an observation "name")
    does not match our constraints.  See the utilities method
    for those expectations/constraints.
    '''
    pass