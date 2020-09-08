from rest_framework.exceptions import ValidationError

class BaseElementSet(object):
    '''
    A `BaseElementSet` is a collection of unique `BaseElement` instances
    (more likely the derived children classes) and is typically used as a
    metadata data structure attached to some "real" data.  For instance, 
    given a matrix of gene expressions, the `ObservationSet` (a child of
    BaseElementSet) is the set of samples that were assayed.  
 
    We depend on the native python set data structure and appropriately
    hashable/comparable `BaseElement` instances (and children).

    This essentially copies most of the functionality of the native set class,
    simply passing through the operations, but includes some additional members
    specific to our application.

    Notably, we disallow (i.e. raise exceptions) if there are attempts to create
    duplicate `BaseElement`s, in contrast to native sets which silently
    ignore duplicate elements.

    A serialized representation (where the concrete `BaseElement` type is `Observation`) 
    would look like:
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

    # the element_typename allows us to keep the logic here, but raise
    # appropriate warnings/exceptions based on the concrete implementation.
    # For instance, an ObservationSet derives from this class.  If someone 
    # passes duplicate elements, we want to tell them it came from specifying
    # "observations" incorrectly.  For a FeatureSet, we would obviously want
    # to warn about incorrect "features".  Child classes will set this field
    # in their __init__(self)
    element_typename = None

    def __init__(self, init_elements, multiple=True):
        '''
        Creates a `BaseElementSet` instance.

        `init_elements` is an iterable of `BaseElement` instances
        `multiple` defines whether we should permit multiple `BaseElement`
          instances.
        '''
        if self.element_typename is None:
            raise NotImplementedError('Set the member "element_typename"'
            ' in your child class implementation')

        if (not multiple) and (len(init_elements) > 1):
            raise ValidationError({'elements':
                'The {element_typename}Set was declared to be a singleton, but'
                ' multiple elements were passed to the constructor.'.format(
                    element_typename=self.element_typename.capitalize())
                })

        self.elements = set(init_elements)
        if len(self.elements) < len(init_elements):
            raise ValidationError({'elements':
                'Attempted to create an {element_typename}Set with a' 
                ' duplicate element.'.format(
                    element_typename=self.element_typename.capitalize())
            })

        self.multiple = multiple


    def add_element(self, new_element):
        '''
        Adds a new `Observation` to the `ObservationSet` 
        (or `Feature` to `FeatureSet`)
        '''

        # if it's a singleton (multiple=False), prevent adding more
        # if the set length is already 1.
        if not self.multiple and len(self.elements) == 1:
            raise ValidationError(
                'Tried to add a second {element_type} to a singleton'
                ' {element_type}Set.'.format(
                    element_type=self.element_typename.capitalize()
                )
            )

        prev_length = len(self.elements)
        self.elements.add(new_element)
        if len(self.elements) == prev_length:
            raise ValidationError(
                'Tried to add a duplicate entry to an {element_type}Set.'.format(
                    element_type=self.element_typename.capitalize()
                )
            )


    def set_intersection(self, other):
        return self.elements.intersection(other.elements)


    def set_difference(self, other):
        return self.elements.difference(other.elements)


    def is_equivalent_to(self, other):
        return self.__eq__(other)


    def is_proper_subset_of(self, other):
        return len(other.set_difference(self)) > 0


    def is_proper_superset_of(self, other):
        return len(self.set_difference(other)) > 0


    def __eq__(self, other):
        return (self.elements == other.elements) \
            & (self.multiple == other.multiple)


    def __hash__(self):
        return hash(tuple(self.elements))


    def __repr__(self):
        s = '\n'.join([str(x) for x in self.elements])
        return 'A set of {element_type}s:\n{obs}'.format(
            obs=s, 
            element_type=self.element_typename.capitalize()
        )

    def to_dict(self):
        d = {}
        d['multiple'] = self.multiple
        d['elements'] = [x.to_dict() for x in self.elements]
        return d