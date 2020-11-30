from api.data_structures import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    StringListAttribute, \
    UnrestrictedStringListAttribute

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

class UnrestrictedStringListConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = UnrestrictedStringListAttribute(user_input)
        return s.value