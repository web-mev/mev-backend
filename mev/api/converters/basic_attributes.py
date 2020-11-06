from api.data_structures import StringAttribute, IntegerAttribute

class BaseAttributeConverter(object):
    pass

class StringConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = StringAttribute(user_input)
        return s.value

class IntegerConverter(BaseAttributeConverter):
    def convert(self, user_input):
        i = IntegerAttribute(user_input)
        return i.value