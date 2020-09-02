import copy

from rest_framework.exceptions import ValidationError

from api.data_structures import create_attribute, \
    IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    DataResourceInputSpec
    

class UserOperationInput(object):
    '''
    This object functions as a base class for formatting and
    validating user-supplied inputs for a particular Operation

    For many input types base off primitives (e.g. `Integer`, `Float`,
    `BoundedInteger`, etc.), we simply take the input spec (a child class 
    of `InputOutputSpec`), merge it with the value that the user submitted
    and then use the base attribute class to validate it.

    For other input types like `DataResourceInputSpec`, we have specialized
    logic that will be implemented in the children classes. 
    '''

    def __init__(self, key, submitted_value, input_spec):
        '''
        The `submitted_value` is the python representation
        of the value provided by the user. For an input corresponding
        to a file, this would be a UUID for a Resource. For a basic integer
        input, this would be a simple int. For a set of observations/samples
        it would be a dictionary meeting the requirements of an
        `api.data_structures.ObservationSet` object.

        The `input_spec` arg is the dictionary representation
        of the specific `InputOutputSpec` class. For instance, an
        input corresponding to a p-value would be of type
        `BoundedFloatInputSpec` and look like:
        ```
        {
            "attribute_type": "BoundedFloat",
            "min": 0.0,
            "max: 1.0,
            "default": 0.05
        }
        ```
        '''
        self.key
        self.submitted_value = submitted_value
        self.input_spec = input_spec

class AttributeBasedUserOperationInput(UserOperationInput):
    '''
    This class handles inputs that are "simple" can use
    the validators contained in the Attribute children
    classes.
    '''

    # a list of the typenames the will use this class to
    # validate. For instance, 'BoundedInteger' is a typename
    # corresponding to the `api.data_structures.attributes.BoundedInteger`
    # class
    TYPENAMES = [
        IntegerAttribute.typename,
        PositiveIntegerAttribute.typename,
        NonnegativeIntegerAttribute.typename,
        FloatAttribute.typename,
        PositiveFloatAttribute.typename,
        NonnegativeFloatAttribute.typename,
        StringAttribute.typename,
        BoundedIntegerAttribute.typename,
        BoundedFloatAttribute.typename,
        BooleanAttribute.typename
    ]

    def __init__(self, key, submitted_value, input_spec):
        super().__init__(key, submitted_value, input_spec)

        d = copy.deepcopy(self.input_spec)
        if 'default' in d:
            d.pop('default')

        # the following function will raise a ValidationError
        # if the submitted value is not sensible for the specific
        # input type.
        instance = create_attribute(key, d)


class DataResourceUserOperationInput(UserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `DataResource` instance.
    '''

    def __init__(self, key, submitted_value, input_spec):
        super().__init__(key, submitted_value, input_spec)

        # The DataResourceInputSpec has a key to indicate
        # whether multiple values are permitted. Depending on that
        # value, we expect a different 'submitted_value'
        expect_many = input_spec[DataResourceInputSpec.MANY_KEY]
        if expect_many:
            if not type(self.submitted_value) == list: 
                raise ValidationError({
                    key: 'Given that the input specification'
                    ' permits multiple values, we expect a list'
                    ' of values.'
                })
            else:
                tmp_val = self.submitted_value
        else: # only single value permitted-- needs to be a string
            if not type(self.submitted_value) == str: 
                raise ValidationError({
                    key: 'Given that the input specification'
                    ' permits only a single value, we expect a'
                    ' string (UUID).'
                })
            else:
                # to handle both cases in the same manner, put the single value
                # into a list
                tmp_val = [self.submitted_value,]    

        # use the DataResourceAttribute type to validate
        # that the value is a UUID (and possibly other
        # logic)
        for v in tmp_val:
            try:
                DataResourceAttribute(v)
            except ValidationError as ex:
                logging.error('Could not validate the user submitted value'
                    ' for a DataResource input: {val}'.format(
                        val=v
                    )
                )   

        # so we have one or more valid UUIDs-- do they correspond to the correct
        # resource types given the input spec?
        #      


# now map the typenames to the class that will be used.
# Recall that the input spec will have an 'attribute_type'
# field that will give us the typename for each input. Then, the dict
# below takes that typename and returns a type.
user_operation_input_mapping = {}
for t in AttributeBasedUserOperationInput.TYPENAMES:
    user_operation_input_mapping[t] = AttributeBasedUserOperationInput