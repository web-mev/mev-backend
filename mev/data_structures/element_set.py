from exceptions import DataStructureValidationException
from data_structures.attribute_types import BaseAttributeType


def merge_element_set(x):
    '''
    A utility method to merge two ElementSet types
    '''
    #TODO: create implementation.
    pass


class BaseElementSet(BaseAttributeType):
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
        "elements": [
            <Observation>,
            <Observation>,
            ...
        ]
    }
    ```
    '''

    def _value_validator(self, val):
        '''
        This method is where the validation of the `ElementSet` (or subclass)
        happens. It's called when the `value` member is set.

        The `BaseAttributeType` class has already handled the case where 
        `val` is None. If we are here, then it is *something* non-None.
        '''
        if not type(val) is dict:
            raise DataStructureValidationException('The constructor for an'
                ' ElementSet or subclass expects a dictionary.')

        # a list (even if empty) is required and addressed by the
        # `elements` key
        try:
            self.elements = val['elements']
        except KeyError:
            raise DataStructureValidationException('An ElementSet type'
                ' requires an "elements" key.')

        self._value = val

    @property
    def elements(self):
        return self._element_list

    @elements.setter
    def elements(self, elements_val):
        if not type(elements_val) is list:
            raise DataStructureValidationException(f'Within a {self.typename},'
                ' the nested "elements" key should address a list.')
        list_of_elements = set()
        for item in elements_val:
            # each item in the list should be an Element subclass 
            # (e.g. Feature, Observation). The implementing class
            # e.g. ObservationSet defines a member that provides
            # the "type" of the nested Element. In the case of the
            # ObservationSet, that's obviously an Observation.
            list_of_elements.add(
                self.elements_type_class(item)
            )
        self._element_list = list_of_elements


    def add_element(self, new_element):
        '''
        Adds a new `Observation` to the `ObservationSet` 
        (or `Feature` to `FeatureSet`)
        '''

        prev_length = len(self._element_list)
        self._element_list.add(new_element)
        if len(self._element_list) == prev_length:
            raise DataStructureValidationException(
                'Tried to add a duplicate entry to an {element_type}Set.'.format(
                    element_type=self.elements_typename.capitalize()
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
        intersection_set = self._element_list.intersection(other._element_list)
        for x in intersection_set:
            attr_dict = {}
            _id = x.id
            el1 = BaseElementSet._get_element_with_id(self._element_list, _id)
            el2 = BaseElementSet._get_element_with_id(other._element_list, _id)
            if el1 and el2:
                # check that we don't have conflicting info. 
                # e.g. if one attribute dict sets a particular attribute
                # to one value and the other is different, reject it.
                # Don't make any assumptions about how that conflict should be handled.
                # these are dicts where the key is a string and the value is a type  
                # like an int, bounded float, etc.
                d1 = el1.attributes
                d2 = el2.attributes
                intersecting_attributes = [x for x in d1 if x in d2]
                for k in intersecting_attributes:
                    if d1[k] != d2[k]:
                        raise DataStructureValidationException(f'When'
                            ' performing an intersection of two sets,'
                            ' encountered a conflict in the attributes.'
                            ' The key "{k}" has differing values of'
                            ' {d1[k]} and {d2[k]}')
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
        union_set = self._element_list.union(other._element_list)
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
        return self._element_list.difference(other.elements)


    def is_equivalent_to(self, other):
        return self.__eq__(other)


    def is_proper_subset_of(self, other):
        return len(other.set_difference(self)) > 0


    def is_proper_superset_of(self, other):
        return len(self.set_difference(other)) > 0


    def __len__(self):
        return len(self._element_list)

    def __eq__(self, other):
        return (self._element_list == other._element_list)


    def __hash__(self):
        return hash(tuple(self._element_list))


    def __repr__(self):
        s = ','.join([str(x) for x in self._element_list])
        return 'A set of {element_type}s:{{{obs}}}'.format(
            obs=s, 
            element_type=self.elements_typename.capitalize()
        )

    def to_dict(self):
        d = {}
        d['elements'] = [x.to_dict() for x in self._element_list]
        return d