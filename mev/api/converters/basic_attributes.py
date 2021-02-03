from api.data_structures import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    StringListAttribute, \
    UnrestrictedStringListAttribute, \
    BooleanAttribute
from api.converters.mixins import CsvMixin
from api.utilities import normalize_identifier
from api.exceptions import StringIdentifierException, AttributeValueError

class BaseAttributeConverter(object):
    pass

class StringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        s = StringAttribute(user_input)
        return {input_key: s.value}

class UnrestrictedStringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        s = UnrestrictedStringAttribute(user_input)
        return {input_key: s.value}
        
class NormalizingStringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        s = UnrestrictedStringAttribute(user_input)
        try:
            s = normalize_identifier(s.value)
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))
        return {input_key: s}

class IntegerConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        i = IntegerAttribute(user_input)
        return {input_key: i.value}

class StringListConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        s = StringListAttribute(user_input)
        return {input_key: s.value}

class StringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Converts a StringList to a csv string
    '''
    def convert(self, input_key, user_input, op_dir):
        s = StringListAttribute(user_input)
        return {input_key: self.to_string(s.value)}

class UnrestrictedStringListConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return {input_key: s.value}

class UnrestrictedStringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return {input_key: self.to_string(s.value)}

class BooleanAsIntegerConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir):
        b = BooleanAttribute(user_input)
        return {input_key: int(b.value)}

class NormalizingListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Takes a list of unrestricted strings and converts them to normalized strings
    '''
    def convert(self, input_key, user_input, op_dir):
        s = UnrestrictedStringListAttribute(user_input)
        try:
            s = [normalize_identifier(x) for x in s.value]
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))
        return {input_key: self.to_string(s)}
