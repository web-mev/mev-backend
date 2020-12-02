from api.data_structures import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    StringListAttribute, \
    UnrestrictedStringListAttribute
from api.converters.mixins import CsvMixin

class BaseAttributeConverter(object):
    pass

class StringConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = StringAttribute(user_input)
        return s.value

class UnrestrictedStringConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = UnrestrictedStringAttribute(user_input)
        return s.value
        
class IntegerConverter(BaseAttributeConverter):
    def convert(self, user_input):
        i = IntegerAttribute(user_input)
        return i.value

class StringListConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = StringListAttribute(user_input)
        return s.value

class StringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Converts a StringList to a csv string
    '''
    def convert(self, user_input):
        s = StringListAttribute(user_input)
        return self.to_string(s.value)

class UnrestrictedStringListConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = UnrestrictedStringListAttribute(user_input)
        return s.value

class UnrestrictedStringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    def convert(self, user_input):
        s = UnrestrictedStringListAttribute(user_input)
        return self.to_string(s.value)