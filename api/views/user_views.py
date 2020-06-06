from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework import generics

from api.serializers.user import UserSerializer
import api.permissions as api_permissions
 

class UserList(generics.ListCreateAPIView):
    '''
    Lists User instances.

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
    Retrieves a specific user.

    Admins may view/modify/delete any user.

    Non-admins may only view/modify/delete their own user instance.
    '''
    # Admins can view detail about any user
    permission_classes = [api_permissions.IsInfoAboutSelf, 
        framework_permissions.IsAuthenticated
    ]

    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
