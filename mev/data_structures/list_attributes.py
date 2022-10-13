import logging

from exceptions import DataStructureValidationException, \
    AttributeValueError

from data_structures.attribute_types import StringAttribute, \
    UnrestrictedStringAttribute, \
    BoundedFloatAttribute, \
    BoundedIntegerAttribute

logger = logging.getLogger(__name__)


class AttributeListMixin(object):

    def _value_validator(self, val):
        if type(val) != list:
            raise DataStructureValidationException('To create a list-type'
                ' attribute you must supply a list.'
            ) 
                
        self._value = []
        for v in val:
            try:
                t = self._instantiate_basic_type(v)
                self._value.append(t)
            except AttributeValueError as ex:
                raise AttributeValueError('Encountered an issue'
                    ' validating one of the nested'
                    f' attributes. Problem was: {ex}')

    def to_dict(self):
        # Note that we only hold simple types, so we 
        # get the 'value' member in the list comprehension below.
        # Otherwise our serialization would produce nested types like
        # [
        #     {'attribute_type': 'String', 'value': 'a'},
        #     ...
        #     {'attribute_type': 'String', 'value': 'c'}
        # ]
        # when we only want ['a',...,'c']
        if self._value:
            val = [x.value for x in self._value]
        else:
            val = None
        return {
            'attribute_type': self.typename,
            'value': val
        }


class StringListAttribute(AttributeListMixin, StringAttribute):
    typename = 'StringList'

    def _instantiate_basic_type(self, v):
        return StringAttribute(v)


class UnrestrictedStringListAttribute(
    AttributeListMixin, UnrestrictedStringAttribute):
    typename = 'UnrestrictedStringList'

    def _instantiate_basic_type(self, v):
        return UnrestrictedStringAttribute(v)


class BoundedIntegerListAttribute(
    AttributeListMixin, BoundedIntegerAttribute):
    typename = 'BoundedIntegerList'

    def _instantiate_basic_type(self, v):
        return BoundedIntegerAttribute(v, 
            min=self._min_value, max=self._max_value)


class BoundedFloatListAttribute(
    AttributeListMixin, BoundedFloatAttribute):
    typename = 'BoundedFloatList'

    def _instantiate_basic_type(self, v):
        return BoundedFloatAttribute(v, 
            min=self._min_value, max=self._max_value)