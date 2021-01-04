from api.data_structures import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    StringListAttribute, \
    UnrestrictedStringListAttribute
from api.converters.mixins import CsvMixin

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