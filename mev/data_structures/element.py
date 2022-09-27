from exceptions import DataStructureValidationException, \
    AttributeValueError

from data_structures.attribute_types import BaseAttributeType
from data_structures.simple_attribute_factory import SimpleAttributeFactory
from data_structures.attribute_types import StringAttribute


class BaseElement(BaseAttributeType):
    '''
    A `BaseElement` is a base class from which we can derive both `Observation`
    and `Features`.  For the purposes of clarity and potential customization, 
    we keep those entities separate.

    As a type of attribute, an `Element` (using an Observation below)
    would look like:
    ```
    {
        "id": <string identifier>,
        "attributes": {
            "keyA": <Attribute>,
            "keyB": <Attribute>
        }
    }
    ```
    We require that all `Element` instances be created with an identifier.
    Equality (e.g. in set operations) is checked using this identifier member

    The nested attributes are objects that dictate a simple attribute
    For instance:
    ```
    {
        "id": <string identifier>,
        "attributes": {
            "stage": {
                "attribute_type": "String",
                "value": "IV"
            },
            "age": {
                "attribute_type": "PositiveInteger",
                "value": 5
            }        
        }
    }
    ```
    The nested dict `attributes` CAN be empty. 
    '''        

    def __init__(self, val, **kwargs):
        # We need to initialize the _value dict. Otherwise, when
        # the constructor (of BaseAttributeType) calls _value_validator,
        # we get missing attribute errors raised by the setter
        # methods. 
        # The reason for doing this is that we are modifying the _value
        # dict in the property setters which allows dynamic
        # updating of the Element instance. During the initial
        # creation, ff we attempt to set the 'id' field in the 
        # setter, we don't have a _value field yet.
        self._value = {}
        super().__init__(val, **kwargs)

    def _value_validator(self, val):
        '''
        This method is where the validation of the `Element` (or subclass)
        happens. It's called when the `value` member is set.

        The `BaseAttributeType` class has already handled the case where 
        `val` is None. If we are here, then it is *something* non-None.
        '''
        if not type(val) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' Element or subclass expects a dictionary.')
        
        try:
            self.id = val.pop('id')
        except KeyError:
            raise DataStructureValidationException('An Element type'
                ' requires an "id" key.')

        # A nested dict of attributes is optional. If it doesn't exist
        # in `val`, we assign an empty dict.
        # Note that setting this ends up calling the setter
        # which attempts validation-- the inner, nested items
        # need to be checked.
        try:
            self.attributes = val.pop('attributes')
        except KeyError:
            self.attributes = {}

        if len(val.keys()) > 0:
            raise DataStructureValidationException('Received extra keys'
                f' when creating a {self.typename} instance:'
                f' {",".join(val.keys())}')

        # now set the _value field:
        #self._set_value_field()
        self._value = {
            'id': self._id,
            'attributes': self._attributes
        }
        
    def _set_value_field(self):
        '''
        The `value` @property (established in the parent class)
        returns self._value when the `value` attribute is accessed.

        In this class _value is a dict.
        Since we allow modification of those dict's attributes, we also
        need to provide a way to update _value. This method gives us one
        single place to set _value
        '''
        pass


    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id_val):
        # If this fails, it will raise an AttributeValueError
        s = StringAttribute(id_val)
        self._id = s.value
        # now reset the 'id' field of_value field so 
        # that changes are reflected 
        self._value['id'] = self._id

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, v):
        if not type(v) is dict:
            raise DataStructureValidationException(f'Within a {self.typename}'
                ' the nested "attributes" key should address a dict/object.')

        validated_attributes = {}
        for key, attr_dict in v.items():
            # key is the name of the attribute
            # attr_dict is a dict, e.g. 
            # {
            #     "attribute_type": "PositiveInteger",
            #     "value":5
            # }
            # Calling the Attribute constructor allows
            # us to check that it's formatted properly.
            try:
                validated_attributes[key] = SimpleAttributeFactory(attr_dict)
            except (DataStructureValidationException, AttributeValueError) as ex:
                s = (f'When attempting to create a {self.typename} instance,'
                    f' the nested attributes contained a key ("{key}") which'
                    ' referenced an improperly formatted attribute.'
                    f' The error was: {ex}')
                raise DataStructureValidationException(s)
        self._attributes = validated_attributes

        # reset the 'attributes' key of _value
        self._value['attributes'] = self._attributes

    def add_attribute(self, attribute_key, attr_dict, overwrite=False):
        '''
        If an additional attribute is to be added, we have to check
        that it is valid and does not conflict with existing attributes
        '''
        if (attribute_key in self._attributes) and (not overwrite):
            raise DataStructureValidationException('The attribute'
                f' identifier {attribute_key} already existed'
                ' and overwriting was blocked.')
        else:
            # we either have a new key or we can overwrite
            # first validate the attribute instance
            self._attributes[attribute_key] = SimpleAttributeFactory(attr_dict)

            # reset the 'attributes' key of _value
            self._value['attributes'] = self._attributes

    def __eq__(self, other):
        '''
        Element equality is determined solely by the identifier field.
        '''
        return self.id == other.id

    def __hash__(self):
        '''
        We implement a hash method so we can use set operations on `Element`
        instances.
        '''
        return hash(self.id)

    def __repr__(self):
        return 'Element ({id})'.format(id=self.id)

    def to_dict(self):
        '''
        Since the _attributes member is a dict that
        can contain nested 'simple' types (e.g. PositiveIntegerAttribute),
        we need to serialize that properly.
        '''
        d = {}
        d['attribute_type'] = self.typename
        if self._value:

            val_dict = {}
            val_dict['id'] = self._id
            serialized_attributes = {}
            for k,v in self._attributes.items():
                serialized_attributes[k] = v.to_dict()
            val_dict['attributes'] = serialized_attributes
            d['value'] = val_dict
            return d
        else:
            d['value'] = None
            return d
