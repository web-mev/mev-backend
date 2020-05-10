import api.exceptions as _exceptions

class ObservationSet(object):
    '''
    An `ObservationSet` is a collection of unique `Observation` instances
    and is typically used as a metadata data structure attached to some "real"
    data.  For instance, given a matrix of gene expressions, the `ObservationSet`
    is the set of samples that were assayed.  
 
    We depend on the native python set data structure and appropriately
    hashable/comparable `Observation` instances.

    This essentially copies most of the functionality of the native set class,
    simply passing through the operations, but I wanted some additional members
    specific to our application.  Without getting too fancy with wrapping methods,
    and similar, it's relatively simple to expose a few set-like operations.

    Notably, we disallow (i.e. raise exceptions) if anyone attempts to create
    duplicate Observations.
    '''

    def __init__(self, observations, multiple=True):
        '''

        '''
        if (not multiple) and (len(observations) > 1):
            raise _exceptions.ObservationSetConstraintException('''
                The ObservationSet was declared to be a singleton, but
                multiple elements were passed to the constructor.
            ''')

        self.observation_set = set(observations)
        if len(self.observation_set) > len(observations):
            raise _exceptions.ObservationSetException('''
                Attempted to create an ObservationSet with a 
                duplicate element.
            ''')

        self.multiple = multiple


    def add_observation(self, new_observation):
        prev_length = len(self.observation_set)
        self.observation_set.add(new_observation)
        if len(self.observation_set) == prev_length:
            raise _exceptions.ObservationSetException('''
                Tried to add a duplicate entry to an ObservationSet.
            ''')


    def set_intersection(self, other):
        return self.observation_set.intersection(other.observation_set)


    def set_difference(self, other):
        return self.observation_set.difference(other.observation_set)


    def is_equivalent_to(self, other):
        return self.__eq__(other)


    def is_superset_of(self, other):
        return len(self.set_difference(other)) > 0


    def __eq__(self, other):
        return self.observation_set == other.observation_set


    def __hash__(self):
        return hash(tuple(self.observation_set))


    def __repr__(self):
        s = '\n'.join([str(x) for x in self.observation_set])
        return 'A set of Observations:\n {obs}'.format(obs=s)