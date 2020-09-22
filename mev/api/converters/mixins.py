class CsvMixin(object):
    @staticmethod
    def to_string(items):
        return ','.join([str(x) for x in items])

class SpaceDelimMixin(object):
    @staticmethod
    def to_string(items):
        return ' '.join([str(x) for x in items])