from .element_set import BaseElementSet

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
        "multiple": <bool>,
        "elements": [
            <Observation>,
            <Observation>,
            ...
        ]
    }
    ```
    '''
    element_typename = 'observation'
        