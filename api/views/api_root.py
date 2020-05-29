from rest_framework.views import APIView
from rest_framework.reverse import reverse
from rest_framework.response import Response

class ApiRoot(APIView):
    '''
    Lists the available "base" endpoints.   
    '''
    def get(self, request, format=None):
        return Response(
            {
                'workspaces': reverse('workspace-list', request=request, format=format),
                'users': reverse('user-list', request=request, format=format),
                'resources': reverse('resource-list', request=request, format=format),
            }
        )
