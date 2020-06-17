import logging

from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.user import UserSerializer, \
    UserRegisterSerializer, \
    PasswordResetSerializer
import api.permissions as api_permissions
from api.utilities import email_utils

logger = logging.getLogger(__name__)

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


class UserRegisterView(APIView):
    '''
    Used to register a new user by email/password
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = UserRegisterSerializer

    def post(self, request, *args, **kwargs):
        logger.info('Received registration request with data: {data}'.format(
            data=request.data))
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            email_utils.send_activation_email(request, user)
            serialized_user = UserSerializer(user, context={'request': request})
            return Response({'user': serialized_user.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)     


class PasswordReset(APIView):
    '''
    Used when a user has forgotten password and
    wants to reset.  Initiates the reset flow
    including the sending of confirmation password.
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            email = data['email']
            return Response({'message': email})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
