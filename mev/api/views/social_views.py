import logging

from django.contrib.auth import login

from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from social_django.utils import psa
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers.social_auth import SocialAuthTokenSerializer

logger = logging.getLogger(__name__)

# This function can be used by multiple oauth2 providers if necessary.
@psa()
def register_by_access_token(request, backend, token):
    '''
    Takes a request object and a backend string.
    Note that the psa decorator takes that backend string
    (which identifies the social auth provider) and attaches
    the proper 'backend' to the request instance so that the remainder
    of the registration flow can happen in social_django
    '''
    logger.info('Starting social authentication')
    try:
        user = request.backend.do_auth(token)
    except Exception as ex:
        raise ValidationError({'access_token': 'There was a problem'
            ' encountered during authentication.  Token may be invalid or expired.'
        })
    if user:
        logger.info('User={user}'.format(user=user))
        login(request, user)
        return user
    else:
        logger.error('Did not retrieve a user following attempt to'
            ' social authenticate.\nrequest={request}\nbackend={backend}'
            '\ntoken={token}'.format(
                request=request,
                backend=backend,
                token=token
            ))
        return None

class GoogleOauth2View(APIView):
    '''
    This allows the front-end to exchange a google access token
    for a WebMEV JWT token 
    '''

    permission_classes = [permissions.AllowAny,]
    serializer_class = SocialAuthTokenSerializer
    provider_name = 'google-oauth2' # this specific string required by social_django to recruit proper backend

    def post(self, request, *args, **kwargs):
        logger.info('Registering or signing-in via Google social auth.')
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            logger.info('Received data: {data}'.format(data=serializer.validated_data))
            google_token = serializer.validated_data['access_token']
            user = register_by_access_token(request, self.provider_name, google_token)
            if user:
                refresh = RefreshToken.for_user(user)

                # they keys in this response are consistent with those returned by the simplejwt
                # package so that username/password and social auth-based accounts return the same
                # JWT response object
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
            return Response({
                'error': 'Could not establish user'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
