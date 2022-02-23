from django.conf import settings

from api.data_structures import StringAttribute, \
    UnrestrictedStringAttribute, \
    IntegerAttribute, \
    StringListAttribute, \
    UnrestrictedStringListAttribute, \
    BooleanAttribute, \
    BoundedFloatAttribute
from api.converters.mixins import CsvMixin
from api.utilities import normalize_identifier
from api.utilities.operations import read_operation_json
from api.exceptions import StringIdentifierException, AttributeValueError

class BaseAttributeConverter(object):
    pass

class StringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = StringAttribute(user_input)
        return {input_key: s.value}

class UnrestrictedStringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = UnrestrictedStringAttribute(user_input)
        return {input_key: s.value}
        
class NormalizingStringConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = UnrestrictedStringAttribute(user_input)
        try:
            s = normalize_identifier(s.value)
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))
        return {input_key: s}

class IntegerConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        i = IntegerAttribute(user_input)
        return {input_key: i.value}

class StringListConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = StringListAttribute(user_input)
        return {input_key: s.value}

class StringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Converts a StringList to a csv string
    '''
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = StringListAttribute(user_input)
        return {input_key: self.to_string(s.value)}

class UnrestrictedStringListConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return {input_key: s.value}

class UnrestrictedStringListToCsvConverter(BaseAttributeConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = UnrestrictedStringListAttribute(user_input)
        return {input_key: self.to_string(s.value)}

class BooleanAsIntegerConverter(BaseAttributeConverter):
    def convert(self, input_key, user_input, op_dir, staging_dir):
        b = BooleanAttribute(user_input)
        return {input_key: int(b.value)}

class NormalizingListToCsvConverter(BaseAttributeConverter, CsvMixin):
    '''
    Takes a list of unrestricted strings and converts them to normalized strings
    '''
    def convert(self, input_key, user_input, op_dir, staging_dir):
        s = UnrestrictedStringListAttribute(user_input)
        try:
            s = [normalize_identifier(x) for x in s.value]
        except StringIdentifierException as ex:
            raise AttributeValueError(str(ex))
        return {input_key: self.to_string(s)}

class BoundedFloatAttributeConverter(BaseAttributeConverter):
        
    def convert(self, input_key, user_input, op_dir, staging_dir):
        operation_json_filepath = os.path.join(op_dir, settings.OPERATION_SPEC_FILENAME)
        op_spec = read_operation_json(operation_json_filepath)
        spec = op_spec['inputs'][input_key]['spec']
        min_val = spec['min']
        max_val = spec['max']
        f = BoundedFloatAttribute(user_input, min=min_val, max=max_val)
        return {input_key: f.value}
