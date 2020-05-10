from rest_framework import serializers, exceptions

from .attributes import AttributeSerializer


class ObservationSerializer(serializers.Serializer):
    id = serializers.RegexField('[a-zA-Z0-9-_\.]+', max_length=50)
    attributes = AttributeSerializer(required=False, many=True)

    def validate(self, data):
        '''
        This is a final check on the deserialization where we can check
        for things like duplicate attribute keys, etc.
        '''
        attribute_list = data['attributes']
        keyset = set()
        for attribute in attribute_list:
            k = attribute.key
            if k in keyset:
                raise serializers.ValidationError(
                    {'attributes':'Duplicate key: {key}'.format(key=k)}
                )
            keyset.add(k)
        return data