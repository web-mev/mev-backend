import logging

from rest_framework.exceptions import ValidationError

from api.data_structures.attributes import BooleanAttribute
from api.data_structures.operation_inputs_and_outputs import InputOutputSpec, \
    IntegerInputOutputSpec, \
    PositiveIntegerInputOutputSpec, \
    NonnegativeIntegerInputOutputSpec, \
    BoundedIntegerInputOutputSpec, \
    FloatInputOutputSpec, \
    PositiveFloatInputOutputSpec, \
    NonnegativeFloatInputOutputSpec, \
    BoundedFloatInputOutputSpec, \
    StringInputOutputSpec, \
    BooleanInputOutputSpec, \
    DataResourceInputOutputSpec

logger = logging.getLogger(__name__)

class OperationInput(object):
    '''
    This class defines a general data structure that holds information about
    inputs to an analysis (`Operation`)
    '''

    def __init__(self, description, name, spec, required=False):

        # a descriptive field to help users
        self.description = description

        # the label of the field in the UI
        self.name = name

        # whether the input field is actually required
        self.required = required

        # a nested object which describes the input itself (e.g. 
        # a number, a string, a file). Of type `InputSpec`
        self.spec = spec
        


class InputSpec(InputOutputSpec):
    '''
    Specialization of InputOutputSpec that dictates
    behavior specific for inputs.
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_representation(self, parent_class):
        d = parent_class.to_representation(self)
        if self.default is not None:
            d['default'] = self.default
        return d


class IntegerInputSpec(IntegerInputOutputSpec):
    pass


class PositiveIntegerInputSpec(PositiveIntegerInputOutputSpec):
    pass


class NonnegativeIntegerInputSpec(NonnegativeIntegerInputOutputSpec):
    pass


class BoundedIntegerInputSpec(BoundedIntegerInputOutputSpec):
    pass


class FloatInputSpec(FloatInputOutputSpec):
    pass


class PositiveFloatInputSpec(PositiveFloatInputOutputSpec):
    pass


class NonnegativeFloatInputSpec(NonnegativeFloatInputOutputSpec):
    pass


class BoundedFloatInputSpec(BoundedFloatInputOutputSpec):
    pass


class StringInputSpec(StringInputOutputSpec):
    pass


class BooleanInputSpec(BooleanInputOutputSpec):
    pass


class DataResourceInputSpec(DataResourceInputOutputSpec):
    '''
    This InputSpec is used for displaying/capturing
    inputs that are related to files.
    ```
    {
        "attribute_type": "DataResource",
        "many": <bool>,
        "resource_types": <list of valid resource types>
    }
    ```
    '''
    MANY_KEY = 'many'
    RESOURCE_TYPES_KEY = 'resource_types'

    def __init__(self, **kwargs):
        DataResourceInputOutputSpec.__init__(self, **kwargs)

    def validate_keyword_args(self, kwargs_dict):
 
        try:
            # use the BooleanAttribute to validate the 'many' key:
            b = BooleanAttribute(kwargs_dict.pop(self.MANY_KEY))
            self.many = b.value
            self.resource_types = kwargs_dict.pop(self.RESOURCE_TYPES_KEY)
        except KeyError as ex:
            raise ValidationError('The "{key}" key is required.'.format(
                key = ex)
            )

        if not type(self.resource_types) == list:
            raise ValidationError('The {key} key needs to be a list.'.format(
                key=self.RESOURCE_TYPES_KEY
                )
            )

        from resource_types import RESOURCE_MAPPING
        for r in self.resource_types:
            if not r in RESOURCE_MAPPING.keys():
                raise ValidationError('The resource type {rt} is not valid.'
                    ' Needs to be one of the following: {csv}.'.format(
                        rt=r,
                        csv=', '.join(RESOURCE_MAPPING.keys())
                    )
                )
        return kwargs_dict

    def to_representation(self):
        i = DataResourceInputOutputSpec.to_representation(self)
        i[self.MANY_KEY] = self.many
        i[self.RESOURCE_TYPES_KEY] = self.resource_types
        return i
        
    #TODO when deserializing the instance, validation will check that
    # the resource types of the UUIDs are valid.

# So we can just the `typename` to retrieve the proper class:
all_input_spec_types = [
    IntegerInputSpec,
    PositiveIntegerInputSpec,
    NonnegativeIntegerInputSpec,
    BoundedIntegerInputSpec,
    FloatInputSpec,
    PositiveFloatInputSpec,
    NonnegativeFloatInputSpec,
    BoundedFloatInputSpec,
    StringInputSpec,
    BooleanInputSpec,
    DataResourceInputSpec,
]
all_input_spec_typenames = [x.typename for x in all_input_spec_types]
input_spec_mapping = dict(zip(all_input_spec_typenames, all_input_spec_types))