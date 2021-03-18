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


class InputMappingException(Exception):
    '''
    Raised if there is an exception to be raised when mapping a user's 
    inputs to job inputs when an ExecutedOperation has been requested.
    '''
    pass


class OperationResourceFileException(Exception):
    '''
    This exception is raised if an Operation specifies user-indepdent
    files that are associated with the Operation, but there is an issue
    finding or reading the file. 
    Raised during the ingestion of the operation
    '''
    pass

class NoResourceFoundException(Exception):
    '''
    Raised as a general exception when a Resource cannot be found.
    '''
    pass

class InactiveResourceException(Exception):
    '''
    Raised when a resource exists, but is inactive. Often used as a "marker"
    to indicate that we cannot perform any modifications to the underlying resource.
    '''
    pass


class OwnershipException(Exception):
    '''
    Raised if there is a conflict between the "owner" of a database resource
    and the requester. Used, for example, to reject requests for a resource/file
    if the requester is NOT the owner.
    '''
    pass


class NonIterableContentsException(Exception):
    '''
    Raised when resource contents are requested, but the data does
    not support iteration. Typical case would be for a JSON-based data
    structure. If the JSON is basically an array, we can iterate. Otherwise
    the concept of pagination is not generalizable (e.g. if the JSON
    is a dict)
    '''
    pass