from data_structures.element_set import BaseElementSet
from data_structures.observation import Observation


class ObservationSet(BaseElementSet):
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
        "elements": [
            <Observation>,
            <Observation>,
            ...
        ]
    }
    ```
    '''
    typename = 'ObservationSet'
    elements_type_class = Observation
    elements_typename = Observation.typename
        
    def set_intersection(self, other):
        intersection_list = super()._set_intersection(other)       
        return ObservationSet({'elements': intersection_list})
        
    def set_union(self, other):
        union_list = super()._set_union(other)
        return ObservationSet({'elements': union_list})

    def set_difference(self, other):
        diff_set = super()._set_difference(other)
        return ObservationSet({'elements': diff_set})