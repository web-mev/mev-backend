from functools import reduce

from constants import OBSERVATION_SET_KEY, \
    FEATURE_SET_KEY

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet


class MetadataMixin(object):

    SETS = 'sets'
    SET_TYPE = 'set_type'

    # this key is a flag (passed with the post payload)
    # which tells us whether to pay attention to the
    # attribute dictionary that accompanies each Observation/Feature
    # Depending on the needs of the request, we may not need to 
    # worry about that dictionary
    IGNORE_ATTR_KEY = 'ignore_attributes'

    elementset_choices = {
        OBSERVATION_SET_KEY: ObservationSet,
        FEATURE_SET_KEY: FeatureSet
    }

    def _get_element_set_class(self, set_type):
        try:
            return self.elementset_choices[set_type]
        except KeyError as ex:
            raise ValidationError({
                self.SET_TYPE: 
                'This must be one of:'
                f' {",".join(self.elementset_choices.keys())}.'})

    def prep(self, request):
        required_keys = [self.SETS, self.SET_TYPE]        
        all_args_present = all(
            [x in request.data.keys() for x in required_keys])
        if all_args_present:
            try:
                ignore_attributes = bool(request.data[self.IGNORE_ATTR_KEY])
            except KeyError:
                ignore_attributes = False # default to being strict
            sets = request.data[self.SETS]
            if len(sets) < 2:
                raise ValidationError('Cannot perform set operations with'
                    ' fewer than two sets.')
            if type(sets) is list:
                element_set_list = []
                elementset_class = self._get_element_set_class(
                    request.data[self.SET_TYPE])
                for s in sets:
                    if ignore_attributes:
                        # if we are ignoring the attributes, we only care about
                        # the identifier
                        el_list = [
                            {'id': x['id']} for x in s['elements']
                        ]
                        s = {
                            'elements': el_list
                        }
                    try:
                        element_set_list.append(
                            elementset_class(s)
                        )
                    except Exception as ex:
                        raise ValidationError({
                            'error': 'Error occurred when parsing the'
                                     ' request payload.'
                        })
                return element_set_list
            else:
                raise ValidationError({self.SETS: 'This key should'
                    ' reference list-like data.'
                })  
        else:
            raise ValidationError({'error': 'This endpoint requires'
                ' the following keys in the payload:'
                f' {",".join(required_keys)}'
            })


class MetadataIntersectView(APIView, MetadataMixin):

    def post(self, request, *args, **kwargs):
        element_set_list = self.prep(request)
        try:
            r = reduce(lambda x, y: x.set_intersection(y), element_set_list)
        except Exception as ex:
            return Response({
                'error': str(ex)
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(r.to_simple_dict())


class MetadataUnionView(APIView, MetadataMixin):

    def post(self, request, *args, **kwargs):
        element_set_list = self.prep(request)
        try:
            r = reduce(lambda x, y: x.set_union(y), element_set_list)
        except Exception as ex:
            return Response({
                'error': str(ex)
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(r.to_simple_dict())


class MetadataSetDifferenceView(APIView, MetadataMixin):

    def post(self, request, *args, **kwargs):
        element_set_list = self.prep(request)
        if len(element_set_list) > 2:
            raise ValidationError('Cannot perform a set difference on'
                ' more than two sets.'
            )
        x, y = element_set_list
        try:
            r = x.set_difference(y)
        except Exception as ex:
            return Response({
                'error': str(ex)
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(r.to_simple_dict())