from data_structures.element_set import BaseElementSet
from data_structures.feature import Feature


class FeatureSet(BaseElementSet):
    '''
    A `FeatureSet` is a collection of unique `Feature` instances
    and is typically used as a metadata data structure attached to some "real"
    data.  For instance, given a matrix of gene expressions, the `FeatureSet`
    is the set of genes.  
 
    We depend on the native python set data structure and appropriately
    hashable/comparable `Feature` instances.

    This essentially copies most of the functionality of the native set class,
    simply passing through the operations, but includes some additional members
    specific to our application.

    Notably, we disallow (i.e. raise exceptions) if there are attempts to create
    duplicate `Feature`s, in contrast to native sets which silently
    ignore duplicate elements.

    A serialized representation would look like:
    ```
    {
        "elements": [
            <Feature>,
            <Feature>,
            ...
        ]
    }
    ```
    '''
    typename = 'FeatureSet'
    elements_type_class = Feature
    elements_typename = Feature.typename
        
    def set_intersection(self, other):
        intersection_list = super()._set_intersection(other)
        return FeatureSet({'elements': intersection_list})

    def set_union(self, other):
        union_list = super()._set_union(other)
        return FeatureSet({'elements': union_list})

    def set_difference(self, other):
        diff_set = super()._set_difference(other)
        return FeatureSet({'elements': diff_set})