import logging

from api.converters.mixins import CsvMixin, SpaceDelimMixin

logger = logging.getLogger(__name__)

class BaseElementSetConverter(object):
    def convert(self, user_input):
        '''
        Simply uses the `id` field and return a list of those string identifiers.
        Typically used for providing sample names to an Operation
        '''
        id_list = []
        for element in user_input['elements']:
            id_list.append(element['id'])
        return id_list


class ObservationSetConverter(BaseElementSetConverter):
    def convert(self, user_input):
        return super().convert(user_input)


class FeatureSetConverter(BaseElementSetConverter):
    def convert(self, user_input):
        return super().convert(user_input)


class ObservationSetCsvConverter(ObservationSetConverter, CsvMixin):
    def convert(self, user_input):
        id_list = ObservationSetConverter.convert(self, user_input)
        return self.to_string(id_list)


class FeatureSetCsvConverter(FeatureSetConverter, CsvMixin):
    def convert(self, user_input):
        id_list = FeatureSetConverter.convert(self, user_input)
        return self.to_string(id_list)
