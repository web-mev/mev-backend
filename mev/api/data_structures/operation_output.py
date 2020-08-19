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

class OperationOutput(object):
    '''
    This class defines a general data structure that holds information about
    outputs from an analysis (`Operation`)
    '''

    def __init__(self, spec):

        # a nested object which describes the output itself (e.g. 
        # a number, a string, a file). Of type `OutputSpec`
        self.output_spec = spec
        


class OutputSpec(InputOutputSpec):
    '''
    Specialization of InputOutputSpec that dictates
    behavior specific for outputs.
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_representation(self, parent_class):
        d = parent_class.to_representation(self)
        if self.default is not None:
            d['default'] = self.default
        return d


class IntegerOutputSpec(IntegerInputOutputSpec):
    pass


class PositiveIntegerOutputSpec(PositiveIntegerInputOutputSpec):
    pass


class NonnegativeIntegerOutputSpec(NonnegativeIntegerInputOutputSpec):
    pass


class BoundedIntegerOutputSpec(BoundedIntegerInputOutputSpec):
    pass


class FloatOutputSpec(FloatInputOutputSpec):
    pass


class PositiveFloatOutputSpec(PositiveFloatInputOutputSpec):
    pass


class NonnegativeFloatOutputSpec(NonnegativeFloatInputOutputSpec):
    pass


class BoundedFloatOutputSpec(BoundedFloatInputOutputSpec):
    pass


class StringOutputSpec(StringInputOutputSpec):
    pass


class BooleanOutputSpec(BooleanInputOutputSpec):
    pass


class DataResourceOutputSpec(DataResourceInputOutputSpec):
    '''
    This OutputSpec is used for describing outputs from an `Operation`

    It is possible to specify a set of outputs with a common type (e.g.
    a bunch of BAM files), but you cannot mix types. File outputs with
    different types will have to be distinct outputs.
    ```
    {
        "attribute_type": "DataResource",
        "many": <bool>,
        "resource_type": <Type of the output>
    }
    ```
    '''
    MANY_KEY = 'many'
    RESOURCE_TYPE_KEY = 'resource_type'

    def __init__(self, **kwargs):
        DataResourceInputOutputSpec.__init__(self, **kwargs)

    def validate_keyword_args(self, kwargs_dict):
 
        try:
            # use the BooleanAttribute to validate the 'many' key:
            b = BooleanAttribute(kwargs_dict.pop(self.MANY_KEY))
            self.many = b.value
            self.resource_type = kwargs_dict.pop(self.RESOURCE_TYPE_KEY)
        except KeyError as ex:
            raise ValidationError('The "{key}" key is required.'.format(
                key = ex)
            )

        if not type(self.resource_type) == str:
            raise ValidationError('The {key} key needs to be a string.'.format(
                key=self.RESOURCE_TYPE_KEY
                )
            )

        from resource_types import RESOURCE_MAPPING
        if not self.resource_type in RESOURCE_MAPPING.keys():
            raise ValidationError('The resource type {rt} is not valid.'
                ' Needs to be one of the following: {csv}.'.format(
                    rt=self.resource_type,
                    csv=', '.join(RESOURCE_MAPPING.keys())
                )
            )
        return kwargs_dict

    def to_representation(self):
        i = DataResourceInputOutputSpec.to_representation(self)
        i[self.MANY_KEY] = self.many
        i[self.RESOURCE_TYPE_KEY] = self.resource_type
        return i
        
    #TODO when deserializing the instance, validation will check that
    # the resource types of the UUIDs are valid.

# So we can just the `typename` to retrieve the proper class:
all_output_spec_types = [
    IntegerOutputSpec,
    PositiveIntegerOutputSpec,
    NonnegativeIntegerOutputSpec,
    BoundedIntegerOutputSpec,
    FloatOutputSpec,
    PositiveFloatOutputSpec,
    NonnegativeFloatOutputSpec,
    BoundedFloatOutputSpec,
    StringOutputSpec,
    BooleanOutputSpec,
    DataResourceOutputSpec,
]
all_output_spec_typenames = [x.typename for x in all_output_spec_types]
output_spec_mapping = dict(zip(all_output_spec_typenames, all_output_spec_types))