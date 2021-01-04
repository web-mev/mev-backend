import logging

from api.converters.mixins import CsvMixin, SpaceDelimMixin

logger = logging.getLogger(__name__)

class BaseElementSetConverter(object):

    def get_id_list(self, user_input):
        '''
        Simply uses the `id` field and return a list of those string identifiers.
        Typically used for providing sample names to an Operation
        '''
        id_list = []
        for element in user_input['elements']:
            id_list.append(element['id'])
        return id_list


class ObservationSetConverter(BaseElementSetConverter):
    def get_id_list(self, user_input):
        return super().get_id_list(user_input)


class FeatureSetConverter(BaseElementSetConverter):
    def get_id_list(self, user_input):
        return super().get_id_list(user_input)


class ObservationSetCsvConverter(ObservationSetConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir):
        id_list = ObservationSetConverter.get_id_list(self, user_input)
        return {input_key: self.to_string(id_list)}


class FeatureSetCsvConverter(FeatureSetConverter, CsvMixin):
    def convert(self, input_key, user_input, op_dir):
        id_list = FeatureSetConverter.get_id_list(self, user_input)
        return {input_key: self.to_string(id_list)}
