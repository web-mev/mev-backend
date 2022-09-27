class Number(object):

    def __init__(self, value, allow_null=False):
        self._allow_null=allow_null
        self.value = value

    def _validator(self, value):
        print('base validator')
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (value is None) and not self._allow_null:
            raise Exception('Cannot be null!')
        elif value is None:
            self._value = None
        else:
            self._validator(value)


class PositiveNumber(Number):
    
    def _validator(self, value):
        if value < 0:
            raise Exception('!!!')
        self._value = value