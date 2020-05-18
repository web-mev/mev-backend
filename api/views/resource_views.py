from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from api.models import Resource
from api.serializers import ResourceSerializer
import api.permissions as api_permissions
from api.utilities.resource_utilities import check_for_resource_operations

class ResourceList(generics.ListCreateAPIView):
    '''
    Lists available Resource instances.

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
        user = self.request.user
        if user.is_staff:
            return Resource.objects.all()
        return Resource.objects.filter(owner=user)
    
    def perform_create(self, serializer):
        serializer.save(requesting_user=self.request.user)


class ResourceDetail(generics.RetrieveUpdateDestroyAPIView):

    # Admins can view/update/delete anyone's Resources, but general users 
    # can only modify their own
    permission_classes = [api_permissions.IsOwnerOrAdmin, 
        framework_permissions.IsAuthenticated
    ]

    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def perform_update(self, serializer):
        '''
        Adds the requesting user to the request payload
        '''
        serializer.save(requesting_user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        '''
        When we receive a delete/destroy request, we have to ensure we
        are not deleting critical data.

        If a Resource is not attached to a Workspace, we can delete
        If a Resource is attached to a Workspace, but has NOT been used
        in any operations then we can safely delete
        If a Resource has been used within a Workspace, we cannot delete
        '''
        instance = self.get_object()
        if instance.workspace is not None:
            has_been_used = check_for_resource_operations(instance)
            if has_been_used:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
