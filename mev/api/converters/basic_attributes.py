from api.data_structures import StringAttribute

class BaseAttributeConverter(object):
    pass

class StringConverter(BaseAttributeConverter):
    def convert(self, user_input):
        s = StringAttribute(user_input)
        return s.value