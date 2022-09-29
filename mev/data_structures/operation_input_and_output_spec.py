import logging
from copy import deepcopy

from exceptions import WebMeVException, \
    DataStructureValidationException

#from data_structures.attribute import Attribute
from data_structures.attribute_factory import AttributeFactory

logger = logging.getLogger(__name__)

    
class InputOutputSpec(object):
    '''
    Base class for objects that describe the inputs or outputs for an `Operation`.
    These are nested inside a `OperationInput` or `OperationOutput` object. 
    Behavior specific to each input type is described in the derived classes

    Note that these are "specifications" for the inputs/outputs, and NOT
    the actual value that a user might fill-in (or an analysis will create).  
    For example, an `Operation` may require a bounded float value (e.g. for a p-value). 
    In the JSON file specifying the inputs to this `Operation`, we have:
    ```
    "spec":{
        "attribute_type": "BoundedFloat",
        "min": <float>,
        "max": <float>,
        "default": <float>
    }
    ```
    When we are creating an `Operation` using this specification, we don't
    have a value-- we simply want to check that the specification is correct
    for the intended attribute_type. That is, given that we are stating it should be a
    BoundedFloat, we need to check that there are min and max values specified.
    We also need to ensure that the default value (if given) is sensible for those
    bounds.
    The child classes below perform those checks.

    When it comes to validating a user's input (so that they can run a specific
    `Operation`), we obviously have to check their input, but that is done in
    another class.
    '''

    DEFAULT_KEY = 'default'

    def __init__(self, spec_dict):
        '''
        The input to the constructor is a dictionary. 

        The `attribute_type` key defines the type of attribute 
        (e.g. a positive integer) that is being specified.

        Beyond that, there are "common" (but optional) keys like
        "default" and type-specific keys (like min/max for bounded
        floats, etc.)
        '''
        if not type(spec_dict) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' input or output specification expects a dictionary.')

        # copy the dict so we work on its copy and don't 
        # cause unintended side effects
        d = deepcopy(spec_dict)

        # see if there is a default specified. If there is,
        # we set `allow_null=False` since we will be using
        # the Attribute class to validate that default.
        # If no default, we need to pass `allow_null=True`
        # so that it doesn't raise an exception.
        try:
            self._default_value = d.pop(self.DEFAULT_KEY)
            allow_null = False
        except KeyError:
            self._default_value = None
            allow_null = True

        # fill-in the `value` field. As mentioned, this allows
        # us to validate the default value.
        d['value'] = self._default_value
        
        # Now try to instantiate the attribute class. If it fails, 
        # then something was wrong with the spec
        try:
            self._attribute_instance = AttributeFactory(d, allow_null=allow_null)
        except WebMeVException as ex:
            # this catches expected failures like missing keys,
            # or bad default values
            logger.info(f'Failed to validate an input/output spec.'
                ' The error was {ex}')
            raise ex
        except Exception as ex:
            logger.error(f'Unexpected failure to validate input/output spec.'
                ' The error was {ex}')
            raise ex

    @property
    def value(self):
        '''
        Use the `value` getter for consistency.
        '''
        return self._attribute_instance

    def to_dict(self):
        d = self._attribute_instance.to_dict()

        # since the underlying attribute may contain a value,
        # we strip that out here. We use this class as a means
        # to verify that a submitted value was valid (since this
        # class LITERALLY is the specification for said input/output).
        # HOWEVER, the spec should not contain the value.
        try:
            d.pop('value')
        except KeyError:
            # not a problem if `value` was missing
            pass 

        if self._default_value is not None:
            d[self.DEFAULT_KEY] = self._default_value

        return d

    def __eq__(self, other):
        a1 = self._attribute_instance
        a2 = other._attribute_instance
        return a1 == a2

