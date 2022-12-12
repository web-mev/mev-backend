from rest_framework import permissions as framework_permissions
from rest_framework import generics

from api.models import Workspace
from api.serializers.workspace import WorkspaceSerializer
import api.permissions as api_permissions


class WorkspaceList(generics.ListCreateAPIView):
    '''
    Lists available Workspace instances.
    '''
    permission_classes = [api_permissions.IsOwner & framework_permissions.IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        return Workspace.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(requesting_user=self.request.user)


class WorkspaceDetail(generics.RetrieveUpdateDestroyAPIView):
    '''
    Retrieves a specific Workspace instance.
    '''
    permission_classes = [api_permissions.IsOwner & framework_permissions.IsAuthenticated]

    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
