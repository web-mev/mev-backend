from django.conf import settings

from helpers import normalize_identifier

from data_structures.attribute_types import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    BooleanAttribute, \
    FloatAttribute
from data_structures.list_attributes import StringListAttribute, \
    UnrestrictedStringListAttribute

from api.converters.mixins import CsvMixin


class BaseAttributeConverter(object):
    '''
    A base class with common attribute conversion behavior
    '''
    def convert_input(self, user_input, op_dir, staging_dir):
        raise NotImplementedError('Need to implement the convert_input method'
            ' for this class')

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        raise NotImplementedError('Need to implement the convert_output method'
            ' for this class')


class SimpleConverterMixin(object):
    '''
    A mixin for basic types that have the same behavior
    for converting inputs and outputs
    '''
    def convert(self, attribute_class, user_input):
        x = attribute_class(user_input)
        return x.value


class StringConverter(BaseAttributeConverter, SimpleConverterMixin):
    def convert_input(self, user_input, op_dir, staging_dir):
        return self.convert(StringAttribute, user_input)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        return self.convert(StringAttribute, output_val)


class UnrestrictedStringConverter(BaseAttributeConverter, SimpleConverterMixin):
    def convert_input(self, user_input, op_dir, staging_dir):
        return self.convert(UnrestrictedStringAttribute, user_input)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        return self.convert(UnrestrictedStringAttribute, output_val)


class NormalizingStringConverter(BaseAttributeConverter, SimpleConverterMixin):

    def convert_input(self, user_input, op_dir, staging_dir):
        s = normalize_identifier(user_input)
        return self.convert(StringAttribute, s)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        s = normalize_identifier(output_val)
        return self.convert(StringAttribute, s)


class IntegerConverter(BaseAttributeConverter, SimpleConverterMixin):

    def convert_input(self, user_input, op_dir, staging_dir):
        return self.convert(IntegerAttribute, user_input)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        return self.convert(IntegerAttribute, output_val)


class FloatConverter(BaseAttributeConverter, SimpleConverterMixin):

    def convert_input(self, user_input, op_dir, staging_dir):
        return self.convert(FloatAttribute, user_input)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        return self.convert(FloatAttribute, output_val)


class StringListConverter(BaseAttributeConverter):

    def convert_input(self, user_input, op_dir, staging_dir):
        s = StringListAttribute(user_input)
        return [x.value for x in s.value]

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        s = StringListAttribute(output_val)
        return [x.value for x in s.value]


class StringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Converts a StringList to a csv string
    '''
    def convert_input(self, user_input, op_dir, staging_dir):
        s = StringListAttribute(user_input)
        return self.to_string([x.value for x in s.value])


class UnrestrictedStringListConverter(BaseAttributeConverter):

    def convert_input(self, user_input, op_dir, staging_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return [x.value for x in s.value]

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        s = UnrestrictedStringListAttribute(output_val)
        return [x.value for x in s.value]


class UnrestrictedStringListToCsvConverter(BaseAttributeConverter, CsvMixin):

    def convert_input(self, user_input, op_dir, staging_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return self.to_string([x.value for x in s.value])


class BooleanAsIntegerConverter(BaseAttributeConverter):

    def convert_input(self, user_input, op_dir, staging_dir):
        b = BooleanAttribute(user_input)
        return int(b.value)

    def convert_output(self, 
        executed_op, user_workspace, output_definition, output_val):
        b = BooleanAttribute(output_val)
        return int(b.value)

class NormalizingListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Takes a list of unrestricted strings and converts 
    them to normalized strings
    '''

    def convert_input(self, user_input, op_dir, staging_dir):
        s = StringListAttribute(
            [normalize_identifier(x) for x in user_input])
        return self.to_string([x.value for x in s.value])
