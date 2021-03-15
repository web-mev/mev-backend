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

    @staticmethod
    def _get_element_with_id(element_list, id):
        '''
        Utility method to get the list element that has 
        the passed id
        '''
        for el in element_list:
            if el.id == id:
                return el

    def _set_intersection(self, other):
        '''
        Returns a list of dicts that represent
        the intersection of the input sets. Will be turned into 
        the properly typed sets by the child/calling class.
        '''
        return_list = []
        intersection_set = self.elements.intersection(other.elements)
        for x in intersection_set:
            attr_dict = {}
            _id = x.id
            el1 = BaseElementSet._get_element_with_id(self.elements, _id)
            el2 = BaseElementSet._get_element_with_id(other.elements, _id)
            if el1 and el2:
                # check that we don't have conflicting info. 
                # e.g. if one attribute dict sets a particular attribute
                # to one value and the other is different, reject it.
                # Don't make any assumptions about how that conflict should be handled.
                d1 = el1.attributes
                d2 = el2.attributes
                intersecting_attributes = [x for x in d1 if x in d2]
                for k in intersecting_attributes:
                    if d1[k] != d2[k]:
                        raise ValidationError('When performing an intersection'
                            ' of two sets, encountered a conflict in the attributes.'
                            ' The key "{k}" has differing values of {x} and {y}'.format(
                                k = k,
                                x = d1[k],
                                y = d2[k]
                            )
                        )
                attr_dict.update(el1.attributes)
                attr_dict.update(el2.attributes)
            return_list.append({'id':_id, 'attributes': attr_dict})
        return return_list

    def _set_union(self, other):
        '''
        Return a list of dicts that represent the UNION of the input sets.
        Will be turned into properly typed sets (e.g. ObservationSet, FeatureSet)
        by the calling class (a child class)
        '''
        return_list = []

        # need to check that the intersecting elements don't have any issues like
        # conflicting attributes:
        intersection_set = self.set_intersection(other)
        union_set = self.elements.union(other.elements)
        for x in union_set:
            _id = x.id
            el = BaseElementSet._get_element_with_id(intersection_set.elements, _id)
            if el: # was part of the intersection set
                return_list.append(el.to_dict())
            else: # was NOT part of the intersection set
                return_list.append({'id':_id, 'attributes': x.attributes})
        return return_list

    def _set_difference(self, other):
        '''
        Returns a set of Observation or Feature instances
        to the calling class of the child, which will be responsible
        for creating a full ObservationSet or FeatureSet
        '''        
        return self.elements.difference(other.elements)


    def is_equivalent_to(self, other):
        return self.__eq__(other)


    def is_proper_subset_of(self, other):
        return len(other.set_difference(self)) > 0


    def is_proper_superset_of(self, other):
        return len(self.set_difference(other)) > 0


    def __len__(self):
        return len(self.elements)

    def __eq__(self, other):
        return (self.elements == other.elements) \
            & (self.multiple == other.multiple)


    def __hash__(self):
        return hash(tuple(self.elements))


    def __repr__(self):
        s = ','.join([str(x) for x in self.elements])
        return 'A set of {element_type}s:{{{obs}}}'.format(
            obs=s, 
            element_type=self.element_typename.capitalize()
        )

    def to_dict(self):
        d = {}
        d['multiple'] = self.multiple
        d['elements'] = [x.to_dict() for x in self.elements]
        return d