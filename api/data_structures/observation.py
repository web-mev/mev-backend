import api.utilities as api_utils

class Observation(object):
    '''
    An `Observation` is the generalization of a "sample" in the typical context
    of biological studies.  One may think of samples and observations as 
    interchangeable concepts.  We call it an observation so that we are not 
    limited by this convention, however.

    `Observation` instances act as metadata and can be used to filter and subset
    the data to which it is associated/attached.
 
    '''

    def __init__(self, id, attribute_list=[]):
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
        self.attributes = attribute_list


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