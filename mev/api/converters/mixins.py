class CsvMixin(object):
    def to_string(self, items):
        return ','.join([x for x in items])


class SpaceDelimMixin(object):
    def to_string(self, items):
        return ' '.join([x for x in items])