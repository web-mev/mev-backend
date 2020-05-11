from rest_framework.exceptions import ValidationError

import api.utilities as api_utils
from .attributes import create_attribute

class Observation(object):
    '''
    An `Observation` is the generalization of a "sample" in the typical context
    of biological studies.  One may think of samples and observations as 
    interchangeable concepts.  We call it an observation so that we are not 
    limited by this convention, however.

    `Observation` instances act as metadata and can be used to filter and subset
    the data to which it is associated/attached.
 
    '''

    def __init__(self, id, attribute_dict={}):
        '''
        We require that all `Observation` instances be created with an identifier.
        Equality (e.g. in set operations) is checked this identier member

        Other attributes may be added, but this is the only required member.
        '''
        # This is a unique identifer.  One could think of this in the same way
        # they would a sample "name"
        normalized_id = api_utils.normalize_identifier(id)
        self.id = normalized_id

        # we permit arbitrary attributes to be associated with Observations
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
        Observation equality is determined solely by the identifier field.
        '''
        return self.id == other.id


    def __hash__(self):
        '''
        We implement a hash method so we can use set operations on `Observation`
        instances.
        '''
        return hash(self.id)


    def __repr__(self):
        return 'Observation ({id})'.format(id=self.id)