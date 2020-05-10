from rest_framework import serializers


class ObservationSetConstraintException(Exception):
    '''
    Raised if a singleton ObservationSet is intended, but the 
    set of Observations has length > 1
    '''
    pass

class ObservationSetException(Exception):
    '''
    Raised if a duplicate element is added to an ObservationSet.
    Unlike the native Python set, we do not silently ignore the addition
    '''
    pass

class StringIdentifierException(Exception):
    '''
    Raised if a String identifier (e.g. an observation "name")
    does not match our constraints.  See the utilities method
    for those expectations/constraints.
    '''
    pass