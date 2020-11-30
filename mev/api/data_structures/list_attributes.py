import logging

from rest_framework.exceptions import ValidationError

from .attributes import StringAttribute, \
    UnrestrictedStringAttribute

logger = logging.getLogger(__name__)

class AttributeListMixin(object):

    def __init__(self, values, **kwargs):
        self.handle_list_of_attributes(values, **kwargs)

    def handle_list_of_attributes(self, values, **kwargs):
        self._value = []
        if type(values) != list:
            raise ValidationError('To create a list-type attribute'
                ' you must supply a list.'
            )
        for v in values:
            try:
                t = self.base_attribute_type(v, **kwargs)
                self._value.append(t)
            except ValidationError as ex:
                err_string = ('Encountered an issue validating one of the nested'
                    ' attributes. Problem was: {ex}'.format(ex=ex)
                )
                raise ValidationError(err_string)

    @property
    def value(self):
        if self._value:
            return [x.value for x in self._value]
        else:
            return self._value

    @value.setter
    def value(self, v):
        if v is not None:
            self.handle_list_of_attributes(v)
        else:
            self._value = None

class StringListAttribute(AttributeListMixin, StringAttribute):
    typename = 'StringList'
    base_attribute_type = StringAttribute


class UnrestrictedStringListAttribute(AttributeListMixin, UnrestrictedStringAttribute):
    typename = 'UnrestrictedStringList'
    base_attribute_type = UnrestrictedStringAttribute

#TODO implement other list-types for the remaining basic attributes.