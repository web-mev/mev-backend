import logging

from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework_simplejwt.views import TokenObtainPairView, \
    TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken

from api.serializers.jwt_tokens import AuthTokenSerializer, \
    RefreshAuthTokenSerializer
from exceptions import ExistingSocialAuthException

logger = logging.getLogger(__name__)


class TokenObtainView(TokenObtainPairView):
    '''
    This endpoint allows a client to submit an email/password
    and receive a JWT token (and refresh token) 
    '''
    permission_classes = [permissions.AllowAny,]
    serializer_class = AuthTokenSerializer

    def _check_for_social_auth(self, request_data):
        email = request_data['email']
        try:
            u = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return None

        if len(u.social_auth.all()) > 0:
            # if the user initially had a email/pwd and
            # subsequently used the social auth mechanism
            # for the same email, we can permit both
            # login methods. This 'if' statement allows that.
            if u.has_usable_password():
                return None
            raise ExistingSocialAuthException()
        else:
            return None

    def post(self, request, *args, **kwargs):
        try:
            self._check_for_social_auth(request.data)
            return super().post(request, *args, **kwargs)
        except ValidationError as ex:
            raise ex
        except ExistingSocialAuthException:
            return Response(
                {drf_api_settings.NON_FIELD_ERRORS_KEY: 'You are attempting to'
                ' authenticate using an email and password. However, this'
                ' account has already been registered using an external'
                ' provider such as Google. Please log in using'
                ' the appropriate authentication provider.'},
                status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response(
                {drf_api_settings.NON_FIELD_ERRORS_KEY: ex.detail},
                status=ex.status_code
            )


class RefreshTokenView(TokenRefreshView):
    '''
    Endpoint for refreshing the JWT auth token.
    '''
    permission_classes = [permissions.AllowAny,]
    serializer_class = RefreshAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ValidationError as ex:
            raise ex
        except InvalidToken as ex:
            return Response(
                {'refresh': ex.detail['detail']},
                status = status.HTTP_400_BAD_REQUEST
            )
        except Exception as ex:
            logger.error('Caught some unexpected error when refreshing'
                f' the authentication token.  Ex={ex}')
            return Response(
                {drf_api_settings.NON_FIELD_ERRORS_KEY: ex},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )