from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from api.models import Resource, Workspace
from api.serializers import ResourceSerializer
import api.permissions as api_permissions

class WorkspaceResourceList(generics.ListAPIView):
    '''
    Lists available Resource instances for a particular Workspace.

    Admins can list all available Resources, but non-admin users 
    can only view their own Resources.
    '''
    
    permission_classes = [
        # admins can do anything
        framework_permissions.IsAdminUser | 

        # regular users need to be authenticated
        # AND are only allowed to list Resources.
        (framework_permissions.IsAuthenticated 
        & 
        api_permissions.ReadOnly)
    ]

    serializer_class = ResourceSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        workspace_pk = self.kwargs['workspace_pk']
        try:
            workspace = Workspace.objects.get(pk=workspace_pk)
        except Workspace.DoesNotExist:
            raise NotFound()
        user = self.request.user
        if user.is_staff:
            return Resource.objects.filter(workspace=workspace)
        elif user == workspace.owner:                 
            return Resource.objects.filter(workspace=workspace)
