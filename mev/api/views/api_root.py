from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class ApiRoot(APIView):
    '''
    Simply responds with a 200 and no payload   
    '''
    # By default all views require authentication. We are OK 
    # with this one being exposed.
    permission_classes = [
        AllowAny
    ]

    def get(self, request, format=None):
        return Response({})
