import copy
import logging

from rest_framework.exceptions import ValidationError

from api.utilities.resource_utilities import get_resource_by_pk
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
from api.models import Resource

logger = logging.getLogger(__name__)

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

    def __init__(self, user, key, submitted_value, input_spec):
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
        self.user = user
        self.key = key
        self.submitted_value = submitted_value
        self.input_spec = input_spec

    def __repr__(self):
        return 'Value: {val} for spec: {spec}'.format(
            val=self.submitted_value,
            spec=self.input_spec
        )

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
    typenames = [
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

    def __init__(self, user, key, submitted_value, input_spec):
        logger.info('Check validity of value {val}'
            ' against input specification: {spec}'.format(
                val=submitted_value,
                spec=input_spec
            )
        )
        super().__init__(user, key, submitted_value, input_spec)

        d = copy.deepcopy(self.input_spec)

        # check for a default:
        try:
            default = d.pop('default')
        except KeyError as ex:
            default = None

        if (self.submitted_value is None) and (default is None):
            logger.info('Both submitted and default values were not specified.')
            raise ValidationError({key: 'The input did not have a'
                ' suitable default value.'
            })
        elif (self.submitted_value is None) and default:
            self.submitted_value = default

        d['value'] = self.submitted_value

        # the following function will raise a ValidationError
        # if the submitted value is not sensible for the specific
        # input type.
        print('Create attr with:', d)
        instance = create_attribute(key, d)


class DataResourceUserOperationInput(UserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `DataResource` instance.
    '''
    typename = DataResourceAttribute.typename

    def __init__(self, user, key, submitted_value, input_spec):
        super().__init__(user, key, submitted_value, input_spec)

        # The DataResourceInputSpec has a key to indicate
        # whether multiple values are permitted. Depending on that
        # value, we expect a different 'submitted_value'
        expect_many = self.input_spec[DataResourceInputSpec.MANY_KEY]
        if expect_many:
            if not type(self.submitted_value) == list:
                logger.info('Invalid payload for an input expecting'
                    ' potentially multiple resources.'
                )
                raise ValidationError({
                    key: 'Given that the input specification'
                    ' permits multiple values, we expect a list'
                    ' of values.'
                })
            else:
                tmp_val = self.submitted_value
        else: # only single value permitted-- needs to be a string
            if not type(self.submitted_value) == str: 
                logger.info('Invalid payload for an input expecting'
                    ' only a single resource. Needs to be a string UUID.'
                )
                raise ValidationError({
                    key: 'Given that the input specification'
                    ' permits only a single value, we expect a'
                    ' string (UUID).'
                })
            else:
                # to handle both cases (single or multiple resources) 
                # in the same manner, put the single value into a list
                tmp_val = [self.submitted_value,]    

        # use the DataResourceAttribute type to validate
        # that the value is a UUID (and possibly other
        # logic necessary to create a DataResourceAttribute)
        # Technically, the database query will catch IDs that are not
        # valid UUIDs, but the DataResourceAttribute constructor could
        # also contain additional validation, etc.
        for v in tmp_val:
            try:
                DataResourceAttribute(v)
            except ValidationError as ex:
                logger.info('Could not validate the user submitted value'
                    ' for a DataResource input: {val}'.format(
                        val=v
                    )
                )
                raise ex   

        # so we have one or more valid UUIDs-- do they correspond to both:
        # - a known Resource owned by the user
        # - the correct resource types given the input spec?
        expected_resource_types = self.input_spec[DataResourceInputSpec.RESOURCE_TYPES_KEY]
        for v in tmp_val:
            try:
                r = get_resource_by_pk(v)
            except Resource.DoesNotExist as ex:
                raise ValidationError({
                    key: 'The UUID ({resource_uuid}) did not match'
                    ' any known resource.'.format(
                        resource_uuid = v
                    )
                })
            # if somehow a user was attempting to use another user's Resource
            if not (r.owner == self.user):
                # don't want to admit that such a file exists (and belongs to 
                # someone else)-- just report that it was not found
                raise ValidationError({
                    key: 'The UUID ({resource_uuid}) did not match'
                    ' any known resource.'.format(
                        resource_uuid = v
                    )
                })
            if not r.resource_type in expected_resource_types:
                logger.info('The resource type {rt} is not compatible'
                    ' with the expected resource types of {all_types}'.format(
                        rt=r.resource_type,
                        all_types = ', '.join(expected_resource_types)
                    )
                )
                raise ValidationError({
                    key: 'The resource ({resource_uuid}, {rt}) did not match'
                    ' the expected type(s) of {all_types}'.format(
                        resource_uuid = v,
                        rt = r.resource_type,
                        all_types = ', '.join(expected_resource_types)
                    )
                })
            if not r.is_active:
                logger.info('The requested Resource ({u}) was'
                ' not active.'.format(
                    u=r.id
                ))
                raise ValidationError({
                    key: 'The resource ({resource_uuid}) was not'
                    ' active and cannot be used.'.format(
                        resource_uuid = v
                    )
                })


# now map the typenames to the class that will be used.
# Recall that the input spec will have an 'attribute_type'
# field that will give us the typename for each input. Then, the dict
# below takes that typename and returns a type.
user_operation_input_mapping = {}
for t in AttributeBasedUserOperationInput.typenames:
    user_operation_input_mapping[t] = AttributeBasedUserOperationInput

# add the other types
user_operation_input_mapping[
    DataResourceUserOperationInput.typename] = DataResourceUserOperationInput