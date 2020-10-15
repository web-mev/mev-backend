import logging

from rest_framework.exceptions import ValidationError

from api.data_structures.attributes import BooleanAttribute
from api.data_structures.operation_input_and_output_spec import InputOutputSpec, \
    IntegerInputOutputSpec, \
    PositiveIntegerInputOutputSpec, \
    NonnegativeIntegerInputOutputSpec, \
    BoundedIntegerInputOutputSpec, \
    FloatInputOutputSpec, \
    PositiveFloatInputOutputSpec, \
    NonnegativeFloatInputOutputSpec, \
    BoundedFloatInputOutputSpec, \
    StringInputOutputSpec, \
    OptionStringInputOutputSpec, \
    BooleanInputOutputSpec, \
    DataResourceInputOutputSpec, \
    ObservationInputOutputSpec, \
    FeatureInputOutputSpec, \
    ObservationSetInputOutputSpec, \
    FeatureSetInputOutputSpec

logger = logging.getLogger(__name__)


class OutputSpec(InputOutputSpec):
    '''
    Specialization of InputOutputSpec that dictates
    behavior specific for outputs.
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_dict(self, parent_class):
        d = parent_class.to_dict(self)
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


class OptionStringOutputSpec(OptionStringInputOutputSpec):
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
    RESOURCE_TYPE_KEY = 'resource_type'

    def __init__(self, **kwargs):
        DataResourceInputOutputSpec.__init__(self, **kwargs)

    def validate_keyword_args(self, kwargs_dict):
 
        try:
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

    def to_dict(self):
        i = DataResourceInputOutputSpec.to_dict(self)
        i[self.MANY_KEY] = self.many
        i[self.RESOURCE_TYPE_KEY] = self.resource_type
        return i


class ObservationOutputSpec(ObservationInputOutputSpec):
    pass


class FeatureOutputSpec(FeatureInputOutputSpec):
    pass


class ObservationSetOutputSpec(ObservationSetInputOutputSpec):
    pass


class FeatureSetOutputSpec(FeatureSetInputOutputSpec):
    pass

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
    OptionStringOutputSpec,
    BooleanOutputSpec,
    DataResourceOutputSpec,
    ObservationOutputSpec,
    FeatureOutputSpec,
    ObservationSetOutputSpec,
    FeatureSetOutputSpec
]
all_output_spec_typenames = [x.typename for x in all_output_spec_types]
output_spec_mapping = dict(zip(all_output_spec_typenames, all_output_spec_types))