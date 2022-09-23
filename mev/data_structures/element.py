from exceptions import DataStructureValidationException

from data_structures.attribute_types import BaseAttributeType
from data_structures.attribute import Attribute
from data_structures.basic_attributes import StringAttribute


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
            self.id = val['id']
        except KeyError:
            raise DataStructureValidationException('An Element type'
                ' requires an "id" key.')

        # A nested dict of attributes is optional. If it doesn't exist
        # in `val`, we assign an empty dict.
        # Note that setting this ends up calling the setter
        # which attempts validation-- the inner, nested items
        # need to be checked.
        self.attributes = val.get('attributes', {})

        self._value = val

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id_val):
        # If this fails, it will raise an AttributeValueError
        s = StringAttribute(id_val)
        self._id = s.value

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, v):
        if not type(v) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' Element or subclass expects a dictionary.')

        validated_attributes = {}
        for key, attr_dict in v.items():
            # key is the name of the attribute
            # attr_dict is a dict.
            # Calling the Attribute constructor allows
            # us to check that it's formatted properly.
            validated_attributes[key] = Attribute(attr_dict)
        self._attributes = validated_attributes

    def add_attribute(self, attribute_key, attr_dict, overwrite=False):
        '''
        If an additional attribute is to be added, we have to check
        that it is valid and does not conflict with existing attributes
        '''
        if (attribute_key in self.attributes) and (not overwrite):
            raise DataStructureValidationException(f'The attribute'
                ' identifier {attribute_key} already existed'
                ' and overwriting was blocked.')
        else:
            # we either have a new key or we can overwrite
            # first validate the attribute instance
            self._attributes[attribute_key] = Attribute(attr_dict)

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
        d = {}
        d['id'] = self._id 
        d['attributes'] = {k:v.to_dict() for k,v in self._attributes.items()}
        return d