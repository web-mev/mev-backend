from .element_set import BaseElementSet
from .feature import Feature

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
        "multiple": <bool>,
        "elements": [
            <Feature>,
            <Feature>,
            ...
        ]
    }
    ```
    '''
    element_typename = 'feature'
        
    def set_intersection(self, other):
        intersection_list = super()._set_intersection(other)
        l = []
        for item in intersection_list:
            l.append(Feature(item['id'], item['attributes']))
        return FeatureSet(l)

    def set_union(self, other):
        union_list = super()._set_union(other)
        l = []
        for item in union_list:
            l.append(Feature(item['id'], item['attributes']))
        return FeatureSet(l)

    def set_difference(self, other):
        diff_set = super()._set_difference(other)
        return FeatureSet(diff_set)