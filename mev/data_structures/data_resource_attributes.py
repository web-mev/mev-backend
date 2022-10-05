import uuid
import logging

from exceptions import AttributeValueError, \
    InvalidAttributeKeywordError, \
    MissingAttributeKeywordError, \
    InvalidResourceTypeException

from data_structures.base_attribute import BaseAttributeType
from data_structures.attribute_types import BooleanAttribute

logger = logging.getLogger(__name__)


def get_all_data_resource_typenames():
    data_resource_types = [
        DataResourceAttribute,
        VariableDataResourceAttribute,
        OperationDataResourceAttribute
    ]
    return [x.typename for x in data_resource_types]


class BaseDataResourceAttribute(BaseAttributeType):
    '''
    Used to specify a reference to one or more Resource
    instances. This class should NOT be used directly. Instead,
    use one of the derived classes.

    Note that this is different than the actual file that holds the
    data. Rather, this is a way to specify that the input corresponds
    to a file.

    Note that "many" controls whether >1 are allowed. It's not an indicator
    for whether there are multiple Resources specified in the "value" key.

    Also note that the "value" of the derived classes is intended to be 
    one or more UUIDs and we validate that they are indeed UUIDs.
    However, we do NOT do any validation that contains API-specific logic.
    That is, this class is not responsible for determining whether an 
    actual Resource (the database model from the api package) has the
    correct type, is able to be used in an analysis, etc. These classes
    are only responsible for validating that the data structure was
    structured correctly.
    '''

    MANY_KEY = 'many'

    def __init__(self, value, **kwargs):

        try:
            v = kwargs.pop(self.MANY_KEY)
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                ' a "many" key.')

        self._validate_many_key(v)
        super().__init__(value, **kwargs)
        
    def _validate_many_key(self, v):
        '''
        Checks that the value passed can be cast as a proper boolean 
        '''
        # use the BooleanAttribute to validate:
        b = BooleanAttribute(v)
        self._many = b.value

    def _value_validator(self, val):
        '''
        Validates that the value (or values)
        are proper UUIDs. 

        This is common for all the derived classes.
        '''
        # if a single UUID was passed, place it into a list:
        
        if (type(val) == str) or (type(val) == uuid.UUID):
            all_vals = [val,]
        elif type(val) == list:
            if self._many == False:
                raise AttributeValueError(f'The values ({val})'
                    ' are inconsistent with the many=False'
                    ' parameter.')
            all_vals = val
        else:
            raise AttributeValueError('Value needs to be either'
                ' a single UUID or a list of UUIDs.')

        try:
            all_vals = [str(x) for x in all_vals]
        except Exception as ex:
            logger.error('An unexpected exception occurred when trying'
                ' to validate a DataResource attribute.'
            )
            raise AttributeValueError('Unexpected validation problem when'
                ' validating a DataResource attribute.')

        for v in all_vals:
            try:
                # check that it is a UUID
                # Note that we can't explicitly check that a UUID
                # corresponds to a Resource database instance
                # as that creates a circular import dependency.
                uuid.UUID(v)
            except ValueError as ex:
                raise AttributeValueError(f'The passed value ({v}) was'
                    ' not a valid UUID.')
            except Exception as ex:
                raise AttributeValueError('Encountered an unknown exception'
                    ' when validating a DataResourceAttribute instance.'
                    f' Value was: {v}')
        self._value = val

    def _check_resource_type_keys(self, available_set, submitted_set):
        '''
        A single method to which checks the submitted `resource_type` key 
        (or `resource_types` for VariableDataResource) and raises an 
        exception if something is incorrect.

        This method is used by child classes and is hence 'private'.

        Both `available_set` and `submitted_set` are literal sets of
        strings
        '''
        diff_set = submitted_set.difference(available_set)
        if diff_set:
            raise InvalidResourceTypeException(f'Received an invalid'
                ' entry or entries when specifying a resource type.'
                f' The following are not valid: {",".join(diff_set)}'
            )

    def to_dict(self):
        d = super().to_dict()
        d[self.MANY_KEY] = self._many
        return d


class DataResourceAttribute(BaseDataResourceAttribute):
    '''
    This class holds info that represents one or more resources
    of a fixed type.

    If the input can be one of multiple types, use one of the other
    classes.

    The serialized representation looks like:
    ```
    {
        "attribute_type": "DataResource",
        "value": <one or more Resource UUIDs>,
        "many": <bool>,
        "resource_type": <str>
    }
    ```  
    `resource_type` dictates the allowable type of resource
    (e.g. integer matrix only). It's value is matched against a controlled
    set of strings.  
    '''
    typename = 'DataResource'
    RESOURCE_TYPE_KEY = 'resource_type'
    REQUIRED_PARAMS = [BaseDataResourceAttribute.MANY_KEY, RESOURCE_TYPE_KEY]

    def __init__(self, value, **kwargs):
        try:
            self.resource_type = kwargs.pop(self.RESOURCE_TYPE_KEY)
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                f' a "{self.RESOURCE_TYPE_KEY}" key.')
        super().__init__(value, **kwargs)

    @property
    def resource_type(self):
        return self._resource_type

    @resource_type.setter
    def resource_type(self, v):
        '''
        Basic setter. Add more logic as necessary
        '''
        self._resource_type = v

    def check_resource_type_keys(self, available_set):
        '''
        Checks that the submitted `resource_type` is valid.
        `available_set` is a set of valid strings
        '''
        # ensure we have a set, just in case we are passed a list
        available_set = set(available_set)

        # create a one item set
        submitted_set = set([self._resource_type])

        self._check_resource_type_keys(available_set, submitted_set)

    def to_dict(self):
        d = super().to_dict()
        d[self.RESOURCE_TYPE_KEY] = self._resource_type
        return d


class OperationDataResourceAttribute(DataResourceAttribute):
    '''
    Used to specify a reference to one or more Resource
    instances which are user-independent, such as database-like 
    resources which are used for analyses.
    ```
    {
        "attribute_type": "OperationDataResource",
        "value": <one or more Resource UUIDs>,
        "many": <bool>,
    }
    ```
    Note that "many" controls whether >1 are allowed. It's not an indicator
    for whether there are multiple Resources specified in the "value" key.
    '''
    typename = 'OperationDataResource'


class VariableDataResourceAttribute(BaseDataResourceAttribute):
    '''
    This class is a specialization of a DataResource which functions to allow
    variable output resource types.

    The reason for this is as follows:
    In earlier iterations of WebMeV, the "type" of output files was fixed; for instance, 
    differential expression analyses always produced 'feature tables'. However, some 
    WebMeV `Operations` perform simple operations such as renaming rows (e.g.
    changing gene names from ENSG to symbols) which can work with multiple file types.
    The fixed system did not allow for such a general tool; we would have to create a 
    virtually identical tool for each type of input file that we want to handle. 
    That's obviously not ideal. Instead, we would like to allow those `Operation`s to 
    create files that have the same type as the input file (e.g. an input feature table 
    would create an output feature table).

    The `VariableDataResource` type is a signal to the code that handles the finalization
    of `ExecutedOperation`s that it should expect an output file that can have multiple types.
    The actual type will be set by the `ExecutedOperation` in its `outputs.json` file. However,
    those details are handled in the "operation spec" classes, not here. This class just establishes
    this as an available type.
    '''
    typename = 'VariableDataResource'

    # since we can accept multiple resource types, we
    # name the key appropriately (at the risk of typos 
    # for resource_type and resource_types).
    RESOURCE_TYPES_KEY = 'resource_types'
    REQUIRED_PARAMS = [BaseDataResourceAttribute.MANY_KEY, RESOURCE_TYPES_KEY]

    def __init__(self, value, **kwargs):
        try:
            self.resource_types = kwargs.pop(self.RESOURCE_TYPES_KEY)
        except KeyError:
            raise MissingAttributeKeywordError('You must specify'
                f' a "{self.RESOURCE_TYPES_KEY}" key.')
        super().__init__(value, **kwargs)

    @property
    def resource_types(self):
        return self._resource_types

    @resource_types.setter
    def resource_types(self, v):
        '''
        Checks that the value passed is a list
        consisting of only valid resource types
        '''
        if not type(v) is list:
            raise InvalidAttributeKeywordError(f'The {self.RESOURCE_TYPES_KEY}'
                ' keyword requires a list.')
        self._resource_types = v

    def check_resource_type_keys(self, available_set):
        '''
        Checks that the submitted `resource_types` is valid.
        `available_set` is a set of valid strings
        '''
        # ensure we have a set, just in case we are passed a list
        available_set = set(available_set)

        # create a set of the resource types
        submitted_set = set(self._resource_types)

        self._check_resource_type_keys(available_set, submitted_set)

    def to_dict(self):
        d = super().to_dict()
        d[self.RESOURCE_TYPES_KEY] = self._resource_types
        return d