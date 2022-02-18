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
    UnrestrictedStringInputOutputSpec, \
    OptionStringInputOutputSpec, \
    BooleanInputOutputSpec, \
    DataResourceInputOutputSpec, \
    VariableDataResourceInputOutputSpec, \
    OperationDataResourceInputOutputSpec, \
    ObservationInputOutputSpec, \
    FeatureInputOutputSpec, \
    ObservationSetInputOutputSpec, \
    FeatureSetInputOutputSpec, \
    StringListInputOutputSpec, \
    UnrestrictedStringListInputOutputSpec

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


class UnrestrictedStringOutputSpec(UnrestrictedStringInputOutputSpec):
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


class VariableDataResourceOutputSpec(VariableDataResourceInputOutputSpec):
    '''
    This OutputSpec is used for describing VARIABLE outputs from an `Operation`

    This allows an `Operation` to define a set of potential resource types
    for a particular output. This allows us to write general tools that will
    work with multiple input types and provide a way to dynamically specify the 
    output resource type.

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

    This `VariableDataResourceOutputSpec` provides a mechanism for an `Operation` developer
    to define the potential output resource types. It is then required that they 
    structure the `outputs.json` file accordingly so that the "finalization" code
    can properly set the actual resource type of any output file(s).
    '''
    RESOURCE_TYPES_KEY = 'resource_types'

    def __init__(self, **kwargs):
        VariableDataResourceInputOutputSpec.__init__(self, **kwargs)

    def validate_keyword_args(self, kwargs_dict):
        try:
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

    def to_dict(self):
        i = VariableDataResourceInputOutputSpec.to_dict(self)
        i[self.MANY_KEY] = self.many
        i[self.RESOURCE_TYPES_KEY] = self.resource_types
        return i


class OperationDataResourceOutputSpec(OperationDataResourceInputOutputSpec):
    '''
    This OutputSpec is used for describing outputs from an `Operation`

    It is possible to specify a set of outputs with a common type (e.g.
    a bunch of BAM files), but you cannot mix types. File outputs with
    different types will have to be distinct outputs.
    ```
    {
        "attribute_type": "OperationDataResource",
        "many": <bool>,
        "resource_type": <Type of the output>
    }
    ```
    '''
    RESOURCE_TYPE_KEY = 'resource_type'

    def __init__(self, **kwargs):
        OperationDataResourceInputOutputSpec.__init__(self, **kwargs)

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
        i = OperationDataResourceInputOutputSpec.to_dict(self)
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

class StringListOutputSpec(StringListInputOutputSpec):
    pass

class UnrestrictedStringListOutputSpec(UnrestrictedStringListInputOutputSpec):
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
    UnrestrictedStringOutputSpec,
    OptionStringOutputSpec,
    BooleanOutputSpec,
    DataResourceOutputSpec,
    VariableDataResourceOutputSpec,
    OperationDataResourceOutputSpec,
    ObservationOutputSpec,
    FeatureOutputSpec,
    ObservationSetOutputSpec,
    FeatureSetOutputSpec,
    StringListOutputSpec,
    UnrestrictedStringListOutputSpec
]
all_output_spec_typenames = [x.typename for x in all_output_spec_types]
output_spec_mapping = dict(zip(all_output_spec_typenames, all_output_spec_types))