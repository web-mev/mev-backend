from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class ElementSetSerializer(serializers.Serializer):

    multiple = serializers.BooleanField()

    def validate(self, data):
        '''
        Validates the entire payload.  Here we check that the number of items
        in the list of `BaseElements` (e.g. `Observation`s) does not conflict
        with the `multiple` flag
        '''
        if (len(data['elements']) > 1) and (not data['multiple']):
            raise ValidationError({'elements':
                'Multiple elements were specified, but the "multiple" key'
                ' was set to False.'})
        return data

    def get_instance(self):
        '''
        A more suggestive way to retrieve the Observation
        instance from the serializer than `save()`, since
        we are not actually saving `BaseElement` subclass 
        instances in the database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)