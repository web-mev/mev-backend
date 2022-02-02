import copy
import logging

from rest_framework.exceptions import ValidationError

from api.data_structures import create_attribute, \
    IntegerAttribute, \
    PositiveIntegerAttribute, \
    NonnegativeIntegerAttribute, \
    FloatAttribute, \
    PositiveFloatAttribute, \
    NonnegativeFloatAttribute, \
    StringAttribute, \
    StringListAttribute, \
    UnrestrictedStringAttribute, \
    UnrestrictedStringListAttribute, \
    OptionStringAttribute, \
    BoundedIntegerAttribute, \
    BoundedFloatAttribute, \
    BooleanAttribute, \
    DataResourceAttribute, \
    DataResourceInputSpec, \
    VariableDataResourceAttribute,\
    VariableDataResourceInputSpec, \
    OperationDataResourceAttribute, \
    OperationDataResourceInputSpec
from api.serializers.observation import ObservationSerializer
from api.serializers.feature import FeatureSerializer
from api.serializers.observation_set import ObservationSetSerializer
from api.serializers.feature_set import FeatureSetSerializer
from api.models import Resource, OperationResource

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

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
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
        self.operation = operation
        self.workspace = workspace
        self.key = key
        self.submitted_value = copy.deepcopy(submitted_value)
        self.input_spec = input_spec
        self.instance = None

    def get_value(self):
        if self.instance:
            return self.instance.to_dict()
            
        else:
            logger.error('The instance attribute was not set when calling'
                ' for the representation of a UserOperationInput as a dict.'
            )
            raise ValidationError('Could not represent a UserOperationInput'
                ' since the instance field was not set.'
            )

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
        UnrestrictedStringAttribute.typename,
        StringListAttribute.typename,
        UnrestrictedStringListAttribute.typename,
        OptionStringAttribute.typename, 
        BoundedIntegerAttribute.typename,
        BoundedFloatAttribute.typename,
        BooleanAttribute.typename
    ]

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        logger.info('Check validity of value {val}'
            ' against input specification: {spec}'.format(
                val=submitted_value,
                spec=input_spec
            )
        )
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

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

        logger.info('In here, self.submitted_value={x}'.format(x=self.submitted_value))
        d['value'] = self.submitted_value

        # the following function will raise a ValidationError
        # if the submitted value is not sensible for the specific
        # input type.
        logger.info('d was: {d}'.format(d=d))
        self.instance = create_attribute(key, d)

    def get_value(self):
        d = self.instance.to_dict()
        return d['value']


class BaseDataResourceUserOperationInput(UserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `DataResource` or `VariableDataResource` instance.

    This class handles the common behavior (such as checking the 'many' key, etc.)
    while child classes handle things specific to a `DataResource`, `VariableDataResource`, etc.
    '''

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)
        expect_many = self.input_spec[DataResourceAttribute.MANY_KEY]
        submitted_vals = self._check_many_vs_input(expect_many)
        self._check_submitted_values(submitted_vals)

        # if we are here, then we have passed all the checks-- assign the
        # self.instance variable 
        self._assign_instance(submitted_value, expect_many)

    def _check_submitted_values(self, submitted_vals):
        for val in submitted_vals:
            r = self._check_resource_uuid(val)
            self._check_resource_workspace(r, self.workspace)
            self._check_resource_types(r)

    def _check_many_vs_input(self, expect_many):
        '''
        The DataResourceAttribute has a key to indicate
        whether multiple values are permitted. Depending on that
        value, we expect a different 'submitted_value' (i.e. if many=True
        then we expect a list.)

        Returns a list of the submitted values (Which are UUIDs)
        '''
        if expect_many:
            if not type(self.submitted_value) == list:
                logger.info('Invalid payload for an input expecting'
                    ' potentially multiple resources.'
                )
                raise ValidationError({
                    self.key: 'Given that the input specification'
                    ' permits multiple values, we expect a list'
                    ' of values.'
                })
            else: # if many and the type of the submission was indeed a list
                tmp_val = self.submitted_value

        else: # only single value permitted-- needs to be a string
            if not type(self.submitted_value) == str: 
                logger.info('Invalid payload for an input expecting'
                    ' only a single resource. Needs to be a string UUID.'
                )
                raise ValidationError({
                    self.key: 'Given that the input specification'
                    ' permits only a single value, we expect a'
                    ' string (UUID).'
                })
            else:
                # to handle both cases (single or multiple resources) 
                # in the same manner, put the single value into a list
                tmp_val = [self.submitted_value,]
        return tmp_val

    def _check_resource_uuid(self, val):
        '''
        The inputs were already determined to be valid UUIDs. This method
        checks that they correspond to actual Resources.
        '''
        # so we have one or more valid UUIDs-- do they correspond to both:
        # - a known Resource owned by the user AND in the workspace?
        # - the correct resource types given the input spec?
        try:
            r = Resource.objects.get(pk=val)
            if not r.is_active:
                logger.info('The requested Resource ({u}) was'
                ' not active.'.format(
                    u=r.id
                ))
                raise ValidationError({
                    self.key: 'The resource ({resource_uuid}) was not'
                    ' active and cannot be used.'.format(
                        resource_uuid = val
                    )
                })
            return r
        except Resource.DoesNotExist as ex:
            raise ValidationError({
                self.key: 'The UUID ({resource_uuid}) did not match'
                ' any known resource.'.format(
                    resource_uuid = val
                )
            })
        except Exception as ex:
            # will catch things like bad UUIDs and also other unexpected errors
            raise ValidationError({self.key: ex})

    def _check_resource_workspace(self, resource, workspace):
        '''
        Need to ensure that the resource is associated with the workspace
        if a workspace is provided (it could be that we are validating
        inputs for an operation not associated with a workspace)
        '''
        # only need to check the workspace compatability if the 
        # workspace arg is not None
        if workspace:
            resource_workspaces = resource.workspaces.all()
            if not (workspace in resource_workspaces):
                raise ValidationError({
                    self.key: 'The UUID ({resource_uuid}) did not match'
                    ' any known resource in your workspace.'.format(
                        resource_uuid = str(resource.pk)
                    )
                })

    def get_value(self):
        d = self.instance.to_dict()
        return d['value']


class DataResourceUserOperationInput(BaseDataResourceUserOperationInput):

    typename = DataResourceAttribute.typename

    def _assign_instance(self, submitted_value, expect_many):
        self.instance = DataResourceAttribute(submitted_value, many=expect_many)

    def _check_resource_types(self, resource):
    
        try:
            expected_resource_type = self.input_spec[DataResourceInputSpec.RESOURCE_TYPE_KEY]
        except KeyError as ex:
            logger.info('The input spec did not contain the required'
                ' key: {k}'.format(k=ex)
            )
            raise ValidationError({
                self.key: 'The input spec did not contain the required'
                ' key: {k}'.format(k=ex)
            })    

        if resource.resource_type != expected_resource_type:
            logger.info('The resource type {rt} is not compatible'
                ' with the expected resource type of {et}'.format(
                    rt=resource.resource_type,
                    et = expected_resource_type
                )
            )
            raise ValidationError({
                self.key: 'The resource ({resource_uuid}, {rt}) did not match'
                ' the expected type of {et}'.format(
                    resource_uuid = str(resource.pk),
                    rt = resource.resource_type,
                    et = expected_resource_type
                )
            })


class VariableDataResourceUserOperationInput(BaseDataResourceUserOperationInput):

    typename = VariableDataResourceAttribute.typename

    def _assign_instance(self, submitted_value, expect_many):
        self.instance = VariableDataResourceAttribute(submitted_value, many=expect_many)

    def _check_resource_types(self, resource):
        try:
            expected_resource_types = self.input_spec[VariableDataResourceInputSpec.RESOURCE_TYPES_KEY]
        except KeyError as ex:
            logger.info('The input spec did not contain the required'
                ' key: {k}'.format(k=ex)
            )
            raise ValidationError({
                self.key: 'The input spec did not contain the required'
                ' key: {k}'.format(k=ex)
            })  

        if not type(expected_resource_types) is list:
            raise ValidationError({
                self.key: 'The resource_types key should contain a list of resource types.'
            })

        if not resource.resource_type in expected_resource_types:
            logger.info('The resource type {rt} is not compatible'
                ' with the expected resource types of {all_types}'.format(
                    rt=resource.resource_type,
                    all_types = ', '.join(expected_resource_types)
                )
            )
            raise ValidationError({
                self.key: 'The resource ({resource_uuid}, {rt}) did not match'
                ' the expected type(s) of {all_types}'.format(
                    resource_uuid = str(resource.pk),
                    rt = resource.resource_type,
                    all_types = ', '.join(expected_resource_types)
                )
            })

class OperationDataResourceUserOperationInput(DataResourceUserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `OperationDataResource` instance.
    '''
    typename = OperationDataResourceAttribute.typename

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

    def _assign_instance(self, submitted_value, expect_many):
        self.instance = OperationDataResourceAttribute(submitted_value, many=expect_many)

    def _check_resource_types(self, resource):
        expected_resource_type = self.input_spec[OperationDataResourceInputSpec.RESOURCE_TYPE_KEY]

        if not resource.resource_type == expected_resource_type:
            logger.info('The resource type {rt} is not compatible'
                ' with the expected resource type of {et}'.format(
                    rt=resource.resource_type,
                    et = expected_resource_type
                )
            )
            raise ValidationError({
                self.key: 'The resource ({resource_uuid}, {rt}) did not match'
                ' the expected type of {et}'.format(
                    resource_uuid = str(resource.pk),
                    rt = resource.resource_type,
                    et = expected_resource_type
                )
            })

    def _check_submitted_values(self, submitted_vals):
        for val in submitted_vals:
            r = self._check_op_resource_uuid(val)
            self._check_resource_types(r)

    def _check_op_resource_uuid(self, val):
        '''
        The inputs were already determined to be valid UUIDs. This method
        checks that they correspond to actual OperationResources.

        We check that the OperationResource was valid for the Operation
        AND that it corresponds to the correct input field for that operation.
        '''
        try:
            r = OperationResource.objects.get(
                pk=val, 
                operation=self.operation, 
                input_field = self.key
            )
            return r
        except OperationResource.DoesNotExist as ex:
            raise ValidationError({
                self.key: 'The UUID ({resource_uuid}) was not valid for'
                    ' the input field "{x}" on Operation with UUID={op_uuid}'.format(
                    resource_uuid = val,
                    op_uuid = str(self.operation.id),
                    x = self.key
                )
            })
        except Exception as ex:
            # will catch things like bad UUIDs and also other unexpected errors
            raise ValidationError({self.key: ex})

class ElementUserOperationInput(UserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a subclass of `BaseElement`, such as an
    `Observation`.
    '''
    typename = None

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)


class ObservationUserOperationInput(ElementUserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `Observation`.
    '''
    typename = 'Observation'

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

        # verify that the Observation is valid by using the serializer
        obs_s = ObservationSerializer(data=self.submitted_value)
        try:
            obs_s.is_valid(raise_exception=True)
        except ValidationError as ex:
            raise ValidationError({key: ex.detail})

        # set the instance:
        self.instance = obs_s.get_instance()


class FeatureUserOperationInput(ElementUserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `Feature`.
    '''
    typename = 'Feature'

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

        # verify that the Feature is valid by using the serializer
        fs = FeatureSerializer(data=self.submitted_value)
        try:
            fs.is_valid(raise_exception=True)
        except ValidationError as ex:
            raise ValidationError({key: ex.detail})

        # set the instance:
        self.instance = fs.get_instance()

class ElementSetUserOperationInput(UserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a subclass of `BaseElementSet`, such as an
    `ObservationSet`.
    '''
    typename = None

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)


class ObservationSetUserOperationInput(ElementSetUserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `ObservationSet`.
    '''
    typename = 'ObservationSet'

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

        # verify that the ObservationSet is valid by using the serializer
        obs_s = ObservationSetSerializer(data=self.submitted_value)
        try:
            obs_s.is_valid(raise_exception=True)
        except ValidationError as ex:
            raise ValidationError({key: ex.detail})

        # set the instance:
        self.instance = obs_s.get_instance()

class FeatureSetUserOperationInput(ElementSetUserOperationInput):
    '''
    This handles the validation of the user's input for an input
    corresponding to a `FeatureSet`.
    '''
    typename = 'FeatureSet'

    def __init__(self, user, operation, workspace, key, submitted_value, input_spec):
        super().__init__(user, operation, workspace, key, submitted_value, input_spec)

        # verify that the FeatureSet is valid by using the serializer
        fs = FeatureSetSerializer(data=self.submitted_value)
        try:
            fs.is_valid(raise_exception=True)
        except ValidationError as ex:
            raise ValidationError({key: ex.detail})
        # set the instance:
        self.instance = fs.get_instance()


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
user_operation_input_mapping[
    VariableDataResourceUserOperationInput.typename] = VariableDataResourceUserOperationInput
user_operation_input_mapping[
    OperationDataResourceUserOperationInput.typename] = OperationDataResourceUserOperationInput 
user_operation_input_mapping[
    ObservationUserOperationInput.typename] = ObservationUserOperationInput
user_operation_input_mapping[
    FeatureUserOperationInput.typename] = FeatureUserOperationInput
user_operation_input_mapping[
    ObservationSetUserOperationInput.typename] = ObservationSetUserOperationInput
user_operation_input_mapping[
    FeatureSetUserOperationInput.typename] = FeatureSetUserOperationInput