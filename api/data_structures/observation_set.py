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
    simply passing through the operations, but includes some additional members
    specific to our application.

    Notably, we disallow (i.e. raise exceptions) if there are attempts to create
    duplicate `Observation`s, in contrast to native sets which silently
    ignore duplicate elements.

    A serialized representation would look like:
    ```
    {
        "multiple": <bool>,
        "observations": [
            <Observation>,
            <Observation>,
            ...
        ]
    }
    ```
    '''

    def __init__(self, init_observations, multiple=True):
        '''
        Creates an `ObservationSet` instance.

        `init_observations` is an iterable of `Observation` instances
        `multiple` defines whether we should permit multiple `Observation`
          instances.
        '''
        if (not multiple) and (len(init_observations) > 1):
            raise _exceptions.ObservationSetConstraintException(
                'The ObservationSet was declared to be a singleton, but'
                ' multiple elements were passed to the constructor.')

        self.observations = set(init_observations)
        if len(self.observations) < len(init_observations):
            raise _exceptions.ObservationSetException(
                'Attempted to create an ObservationSet with a' 
                ' duplicate element.')

        self.multiple = multiple


    def add_observation(self, new_observation):
        '''
        Adds a new `Observation` to the `ObservationSet`
        '''

        # if it's a singleton (multiple=False), prevent adding more
        # if the set length is already 1.
        if not self.multiple and len(self.observations) == 1:
            raise _exceptions.ObservationSetException(
                'Tried to add a second Observation to a singleton'
                ' ObservationSet.'
            )

        prev_length = len(self.observations)
        self.observations.add(new_observation)
        if len(self.observations) == prev_length:
            raise _exceptions.ObservationSetException(
                'Tried to add a duplicate entry to an ObservationSet.'
            )


    def set_intersection(self, other):
        return self.observations.intersection(other.observations)


    def set_difference(self, other):
        return self.observations.difference(other.observations)


    def is_equivalent_to(self, other):
        return self.__eq__(other)


    def is_proper_subset_of(self, other):
        return len(other.set_difference(self)) > 0


    def is_proper_superset_of(self, other):
        return len(self.set_difference(other)) > 0


    def __eq__(self, other):
        return (self.observations == other.observations) \
            & (self.multiple == other.multiple)


    def __hash__(self):
        return hash(tuple(self.observations))


    def __repr__(self):
        s = '\n'.join([str(x) for x in self.observations])
        return 'A set of Observations:\n{obs}'.format(obs=s)