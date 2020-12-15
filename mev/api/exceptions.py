class StringIdentifierException(Exception):
    '''
    Raised if a String identifier (e.g. an observation "name")
    does not match our constraints.  See the utilities method
    for those expectations/constraints.
    '''
    pass


class AttributeValueError(Exception):
    '''
    Raised by the attribute subclasses if something is amiss.
    For example, if we try to create an IntegerAttribute with
    a string.
    '''
    pass


class InvalidAttributeKeywords(Exception):
    '''
    Raised if invalid keyword args are passed to the constructor of
    an Attribute subclass
    '''
    pass