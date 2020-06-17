import logging

from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers.user import UserSerializer, \
    UserRegisterSerializer, \
    PasswordResetSerializer, \
    UserActivateSerializer, \
    ResendActivationSerializer, \
    PasswordResetConfirmSerializer
import api.permissions as api_permissions
from api.utilities import email_utils

logger = logging.getLogger(__name__)

User = get_user_model()

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
            return User.objects.all()
        return User.objects.filter(pk=user.pk)


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

    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserRegisterView(APIView):
    '''
    Used to register a new user by email/password
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = UserRegisterSerializer

    EXISTING_USER_MESSAGE = 'This user already exists.'

    def post(self, request, *args, **kwargs):
        logger.info('Received registration request with data: {data}'.format(
            data=request.data))
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            email = validated_data['email']
            try:
                user = User.objects.get(email=email)
                return Response({
                    'email': self.EXISTING_USER_MESSAGE}, 
                    status=status.HTTP_400_BAD_REQUEST) 
            except User.DoesNotExist:
                user = serializer.save()
                email_utils.send_activation_email(request, user)
                serialized_user = UserSerializer(user, context={'request': request})
                return Response({'user': serialized_user.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)     

class ResendActivationView(APIView):
    '''
    If a user's token expires, they exist in our system, but can't
    activate.  This sends them another email with a new token
    '''    
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = ResendActivationSerializer

    ALREADY_ACTIVE_MESSAGE = 'This account was already activated.'

    def post(self, request, *args, **kwargs):
        logger.info('Received request to re-send activation'
            ' email with data: {data}'.format(
                data=request.data)
            )
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            if user.is_active:
                return Response({
                    'email': self.ALREADY_ACTIVE_MESSAGE}, 
                    status=status.HTTP_400_BAD_REQUEST)     
            email_utils.send_activation_email(request, user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)     

class UserActivateView(APIView):
    '''
    This validates the uid/token and activates the user once they click on
    the link in their email
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = UserActivateSerializer

    def post(self, request, *args, **kwargs):
        logger.info('Received activation request with data: {data}'.format(
            data=request.data))
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            user.is_active = True
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)     


class PasswordResetView(APIView):
    '''
    Used when a user has forgotten password and
    wants to reset.  Initiates the reset flow
    including the sending of confirmation password.
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            user = serializer.user
            email_utils.send_password_reset_email(request, user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    '''
    Used when a user has clicked on a reset link
    and is sending a UID (encoded), a token, a new password,
    and a re-typed confirmation of that password
    '''
    permission_classes = [framework_permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            user = serializer.user
            print('set password to', validated_data['password'])
            user.set_password(validated_data['password'])
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
