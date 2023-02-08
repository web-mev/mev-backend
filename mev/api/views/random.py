import numpy as np

from rest_framework.views import APIView
from rest_framework.response import Response


class RandomView(APIView):
    '''
    A view that can be used for testing polling processes
    for the the frontend. 
    '''

    def get(self, request, format=None):
        x = np.random.random()
        threshold = 0.2
        if x < threshold:
            return Response({'message': 'complete'}, status=200)
        else:
            return Response({'message': 'running'}, status=204)
