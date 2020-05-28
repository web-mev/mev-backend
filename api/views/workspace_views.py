from rest_framework import permissions as framework_permissions
from rest_framework import generics

from api.models import Workspace
from api.serializers import WorkspaceSerializer
import api.permissions as api_permissions


class WorkspaceList(generics.ListCreateAPIView):
    '''
    Lists available Workspace instances.

    Admins can list all available Workspaces.
    
    Non-admin users can only view their own Workspaces.
    '''
    
    permission_classes = [api_permissions.IsOwnerOrAdmin, 
        framework_permissions.IsAuthenticated
    ]

    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        user = self.request.user
        if user.is_staff:
            return Workspace.objects.all()
        return Workspace.objects.filter(owner=user)
    
    def perform_create(self, serializer):
        serializer.save(requesting_user=self.request.user)


class WorkspaceDetail(generics.RetrieveUpdateDestroyAPIView):
    '''
    Retrieves a specific Workspace instance.

    Admins may access any user's Workspace.

    Non-admin users may only access their own Workspace instances.
    '''

    # Admins can view/update/delete anyone's Workspaces, but general users 
    # can only modify their own
    permission_classes = [api_permissions.IsOwnerOrAdmin, 
        framework_permissions.IsAuthenticated
    ]

    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer