class WebMeVException(Exception):
    '''
    This base class allows us to organize our WebMeV-specific
    exceptions and catch them (and derived classes)specifically. 
    '''
    pass


class StringIdentifierException(WebMeVException):
    '''
    Raised if a String identifier (e.g. an observation "name")
    does not match our constraints.
    '''
    pass


class NullAttributeError(WebMeVException):
    '''
    Raised if a None value is passed as the value
    for an attribute that does not allow nulls.
    '''
    pass


class AttributeValueError(WebMeVException):
    '''
    Raised by the attribute subclasses if something is amiss.
    For example, if we try to create an IntegerAttribute with
    a string.
    '''
    pass


class MissingAttributeKeywordError(WebMeVException):
    '''
    Raised if required keyword args are missing
    '''
    pass


class AttributeTypeError(WebMeVException):
    '''
    Raised if an invalid attribute is requested.
    For instance, if there is a typo in an operation spec
    and the user needs to correct the type.
    '''
    pass


class InvalidAttributeKeywordError(WebMeVException):
    '''
    Raised if invalid keyword args are used.

    An example would be if we declare a bounded integer type
    and provide the min or max as a float.
    '''
    pass


class InputMappingException(WebMeVException):
    '''
    Raised if there is an exception to be raised when mapping a user's 
    inputs to job inputs when an ExecutedOperation has been requested.
    '''
    pass


class OperationResourceFileException(WebMeVException):
    '''
    This exception is raised if an Operation specifies user-indepdent
    files that are associated with the Operation, but there is an issue
    finding or reading the file. 
    Raised during the ingestion of the operation
    '''
    pass


class NoResourceFoundException(WebMeVException):
    '''
    Raised as a general exception when a Resource cannot be found.
    '''
    pass


class InactiveResourceException(WebMeVException):
    '''
    Raised when a resource exists, but is inactive. Often used as a "marker"
    to indicate that we cannot perform any modifications to the underlying resource.
    '''
    pass


class ExecutedOperationInputOutputException(WebMeVException):
    '''
    This is raised if we can't validate an input or output.

    Note that this isn't for simple cases like a bad user input
    (e.g. a pvalue > 1).

    This is for cases that are possible, but unlikely.
    An example would be passing a valid resource pk (UUID)
    as an input. Technically, it's possible to POST a UUID
    to a file that the user doesn't own (or is not part of
    their workspace). Such an event is unlikely if using
    the frontend application, but not impossible
    if the POST request submitted by other means.
    '''
    pass


class OwnershipException(WebMeVException):
    '''
    Raised if there is a conflict between the "owner" of a database resource
    and the requester. Used, for example, to reject requests for a resource/file
    if the requester is NOT the owner.
    '''
    pass


class NonIterableContentsException(WebMeVException):
    '''
    Raised when resource contents are requested, but the data does
    not support iteration. Typical case would be for a JSON-based data
    structure. If the JSON is basically an array, we can iterate. Otherwise
    the concept of pagination is not generalizable (e.g. if the JSON
    is a dict)
    '''
    pass


class OutputConversionException(WebMeVException):
    '''
    Raised when the output of an `ExecutedOperation` has an issue. Examples
    include failure to format the output payload or a failure of the validation
    functions for the output files (e.g. it's not actually an integer matrix as
    we expect)
    '''
    pass


class StorageException(WebMeVException):
    '''
    This is raised as part of storage operations where failure is predicted (i.e. 
    it's not a generic catch-all failure that we did not expect)
    '''
    pass


class ResourceValidationException(WebMeVException):
    '''
    This is raised if any part of the resource validation process fails. This helps
    distinguish predictable validation errors from those that are unexpected.
    '''
    pass


class DataStructureValidationException(WebMeVException):
    '''
    This is raised if one of the underlying data structures has a formatting
    or validation issue.
    '''
    pass


class InvalidResourceTypeException(WebMeVException):
    '''
    This is raised if an invalid shorthand key is encountered
    when working with DataResource objects
    '''
    pass


class InvalidRunModeException(WebMeVException):
    '''
    Raised if an operation spec specifies an operation 
    mode that is not valid
    '''
    pass


class JobSubmissionException(WebMeVException):
    '''
    Used for raising a specific exception related to unexpected
    behavior when submitting jobs. Examples include a 4xx, 500
    response from Cromwell, etc.
    '''
    pass


class MissingRequiredFileException(WebMeVException):
    '''
    Used if one of the files is missing in the Operation
    repository (e.g. a operation_spec.json, etc.)
    '''
    pass