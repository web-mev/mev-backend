from rest_framework import serializers, exceptions

from api.data_structures import ObservationSet
from api.serializers import ObservationSerializer

class ObservationSetSerializer(serializers.Serializer):

    multiple = serializers.BooleanField()
    observations = ObservationSerializer(required=False, many=True)

    def validate(self, data):
        '''
        Validates the entire payload.  Here we check that the number of items
        in the list `Observation`s does not conflict with the `multiple` flag
        '''
        if (len(data['observations']) > 1) and (not data['multiple']):
            raise exceptions.ValidationError({'observations':
                'Multiple observations were specified, but the "multiple" key'
                ' was set to False.'})
        return data
        

    def create(self, validated_data):
        '''
        Returns an ObservationSet instance from the validated
        data.
        '''
        obs_list = []
        for obs_dict in validated_data['observations']:
            # the validated data has the Observation info as an OrderedDict
            # below, we use the ObservationSerializer to turn that into
            # proper Observation instance.
            obs_serializer = ObservationSerializer(data=obs_dict)
            obs = obs_serializer.get_instance()
            obs_list.append(obs)
        return ObservationSet(
            obs_list, 
            validated_data['multiple']
        )

    def get_instance(self):
        '''
        A more suggestive way to retrieve the Observation
        instance from the serializer than `save()`, since
        we are not actually saving Observation instances in the
        database.
        '''
        self.is_valid(raise_exception=True)
        return self.create(self.validated_data)