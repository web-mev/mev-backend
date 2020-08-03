from rest_framework.exceptions import ValidationError

import api.utilities as api_utils
from .attributes import create_attribute

class BaseElement(object):
    '''
    A `BaseElement` is a base class from which we can derive both `Observation`
    and `Features`.  For the purposes of clarity, we keep those entities separate.
    Yet, their behavior and structure are very much the same.  This also allows
    us to add custom behavior to each at a later time if we require.

    An `Element` is structured as:
    ```
    {
        "id": <string identifier>,
        "attributes": {
            "keyA": <Attribute>,
            "keyB": <Attribute>
        }
    }
    ```
 
    '''

    def __init__(self, id, attribute_dict={}):
        '''
        We require that all `Element` instances be created with an identifier.
        Equality (e.g. in set operations) is checked this identier member

        Other attributes may be added, but this is the only required member.
        '''
        # This is a unique identifer.  One could think of this in the same way
        # they would a sample "name"

        if type(id) == str:
            self.id = id
        else:
            raise api_exceptions.StringIdentifierException(
                'The name "{name}" was not'
                ' a string.'.format(name=id))

        # we permit arbitrary attributes to be associated with `Element`s
        # They have to be formatted as a dictionary.  Typically, the associated
        # serializer will catch the problem before it reaches here.  But we also
        # guard against it here.
        if type(attribute_dict) == dict:
            self.attributes = attribute_dict
        else:
            raise ValidationError('The attributes must be formatted as a dictionary.')


    def add_attribute(self, attribute_key, attr_dict, overwrite=False):
        '''
        If an additional attribute is to be added, we have to check
        that it is valid and does not conflict with existing attributes
        '''
        if (attribute_key in self.attributes) and (not overwrite):
            raise ValidationError('The attribute identifier {attribute_key}'
            ' already existed in the attributes.')
        else:
            # we either have a new key or we can overwrite
            # first validate the attribute instance
            attr_instance = create_attribute(attribute_key, attr_dict)
            self.attributes[attribute_key] = attr_instance


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