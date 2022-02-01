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


class InputSpec(InputOutputSpec):
    '''
    Specialization of InputOutputSpec that dictates
    behavior specific for inputs.
    '''
    def __init__(self, **kwargs):
        InputOutputSpec.__init__(self, **kwargs)

    def to_dict(self, parent_class):
        d = parent_class.to_dict(self)
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


class UnrestrictedStringInputSpec(UnrestrictedStringInputOutputSpec):
    pass

class OptionStringInputSpec(OptionStringInputOutputSpec):
    pass


class BooleanInputSpec(BooleanInputOutputSpec):
    pass


class DataResourceInputSpec(DataResourceInputOutputSpec):
    '''
    This InputSpec is used for displaying/capturing
    inputs that are related to files. This type permits only
    a single input resource type
    ```
    {
        "attribute_type": "DataResource",
        "many": <bool>,
        "resource_type": <a valid resource type>
    }
    ```
    Note that the `many` key is a field of the underlying DataResourceAttribute
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

class VariableDataResourceInputSpec(VariableDataResourceInputOutputSpec):
    '''
    This InputSpec is used for displaying/capturing
    inputs that are related to files. This type permits multiple input
    file types, specified throug the list provided in `resource_types`
    ```
    {
        "attribute_type": "DataResource",
        "many": <bool>,
        "resource_types": <list of valid resource types>
    }
    ```
    Note that the `many` key is a field of the underlying VariableDataResourceAttribute
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



class OperationDataResourceInputSpec(OperationDataResourceInputOutputSpec):
    '''
    This InputSpec is used for displaying/capturing
    inputs that are user-independent and related to a specific
    Operation instance.
    ```
    {
        "attribute_type": "OperationDataResource",
        "many": <bool>,
        "resource_types": <list of valid resource types>
    }
    ```
    Note that the `many` key is a field of the underlying OperationDataResourceAttribute

    We derive from DataResourceInputSpec so we can re-use some of the methods there
    '''

    RESOURCE_TYPES_KEY = 'resource_types'

    def __init__(self, **kwargs):
        OperationDataResourceInputOutputSpec.__init__(self, **kwargs)

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
        i = OperationDataResourceInputOutputSpec.to_dict(self)
        i[self.MANY_KEY] = self.many
        i[self.RESOURCE_TYPES_KEY] = self.resource_types
        return i


class ObservationInputSpec(ObservationInputOutputSpec):
    pass


class FeatureInputSpec(FeatureInputOutputSpec):
    pass


class ObservationSetInputSpec(ObservationSetInputOutputSpec):
    pass


class FeatureSetInputSpec(FeatureSetInputOutputSpec):
    pass

class StringListInputSpec(StringListInputOutputSpec):
    pass

class UnrestrictedStringListInputSpec(UnrestrictedStringListInputOutputSpec):
    pass

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
    UnrestrictedStringInputSpec,
    OptionStringInputSpec,
    BooleanInputSpec,
    DataResourceInputSpec,
    OperationDataResourceInputSpec,
    ObservationInputSpec,
    FeatureInputSpec,
    ObservationSetInputSpec,
    FeatureSetInputSpec,
    StringListInputSpec,
    UnrestrictedStringListInputSpec
]
all_input_spec_typenames = [x.typename for x in all_input_spec_types]
input_spec_mapping = dict(zip(all_input_spec_typenames, all_input_spec_types))