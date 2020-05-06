from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework.reverse import reverse
from rest_framework.response import Response

from api.models import Workspace
from api.serializers import WorkspaceSerializer, UserSerializer
import api.permissions as api_permissions

class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response(
            {
                'workspaces': reverse('workspace-list', request=request, format=format),
                'users': reverse('user-list', request=request, format=format),
            }
        )


class WorkspaceList(generics.ListCreateAPIView):
    '''
    Lists available Workspace instances.

    Admins can list all available Workspaces, but non-admin users 
    can only view their own Workspaces.
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

    # Admins can view/update/delete anyone's Workspaces, but general users 
    # can only modify their own
    permission_classes = [api_permissions.IsOwnerOrAdmin, 
        framework_permissions.IsAuthenticated
    ]

    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer

    

class UserList(generics.ListCreateAPIView):
    '''
    Lists available User instances.

    Admins can view and create new users.
    Non-admin users can only view their own information.
    '''
    
    permission_classes = [api_permissions.IsInfoAboutSelf, 
        framework_permissions.IsAdminUser
    ]
    serializer_class = UserSerializer

    def get_queryset(self):
        '''
        Note that the generic `permission_classes` applied at the class level
        do not provide access control when accessing the list.  

        This method dictates that behavior.
        '''
        user = self.request.user
        if user.is_staff:
            return get_user_model().objects.all()
        return get_user_model().objects.filter(pk=user.pk)


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    '''
    Admins may view/modify/delete any user.

    Non-admins may only view/modify/delete themself
    '''
    # Admins can view detail about any user
    permission_classes = [api_permissions.IsInfoAboutSelf, 
        framework_permissions.IsAuthenticated
    ]

    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer