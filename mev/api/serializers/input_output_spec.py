from rest_framework import serializers

class InputOutputSpecSerializer(serializers.BaseSerializer):
    '''
    Serializes/deserializes InputOutputSpec instances.
    '''

    def to_representation(self, instance):
        return instance.to_representation()

    def get_instance(self):
        '''
        The `save` method of serializers could work here, but this 
        naming is more suggestive since we are not actually saving
        to any database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)