import logging

import backoff

from django.contrib.auth import login
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from social_django.utils import psa
import social_core.exceptions
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers.social_auth import SocialAuthTokenSerializer
from api.views.mixins import SchemaMixin

logger = logging.getLogger(__name__)

@backoff.on_predicate(backoff.expo, lambda x: x is None, max_tries=settings.MAX_RETRIES)
def do_auth(request, token):
    try:
        user = request.backend.do_auth(token)
        return user
    except social_core.exceptions.AuthForbidden as ex:
        # this exception is raised if the token is invalid
        logger.info('Exception of type social_core.exceptions.AuthForbidden'
            ' was raised. Token likely invalid.'
        )
        raise ValidationError({'provider_token': 'There was a problem'
            ' encountered during authentication.  Token may be invalid or expired.'
        })
    except Exception as ex:
        # Catch other types of exception.  Return None so that this
        # function is tried again.
        logger.info('Caught another type of exception when attempting'
            ' to authenticate with social auth provider.  Will retry.'
            f' Exception was: {ex}.')
        return None

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

    # Get the authenticated user.  The do_auth function does retries.
    user = do_auth(request, token)

    if user:
        logger.info(f'User={user}')
        login(request, user)
        return user
    else:
        logger.error('Did not retrieve a user following attempt to'
            f' social authenticate.\nrequest={request}\nbackend={backend}'
            f'\ntoken={token}')
        return None

class GoogleOauth2View(APIView, SchemaMixin):
    '''
    This endpoint allows a client to exchange a google access token
    for a WebMEV JWT token 
    '''

    permission_classes = [permissions.AllowAny,]
    serializer_class = SocialAuthTokenSerializer

    # this specific string required by social_django to recruit proper backend
    provider_name = 'google-oauth2'

    def post(self, request, *args, **kwargs):
        logger.info('Registering or signing-in via Google social auth.')
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            logger.info(f'Received data: {serializer.validated_data}')
            google_token = serializer.validated_data['provider_token']
            user = register_by_access_token(
                request, self.provider_name, google_token)
            if user:
                refresh = RefreshToken.for_user(user)

                # they keys in this response are consistent with those 
                # returned by the simplejwt package so that username/password
                # and social auth-based accounts return the same JWT
                # response object
                return_serializer = self.serializer_class({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
                return Response(return_serializer.data)
            return Response({
                'error': 'Could not establish user'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
