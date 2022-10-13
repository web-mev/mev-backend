import logging

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

logger = logging.getLogger(__name__)


class TokenObtainView(TokenObtainPairView):
    '''
    This endpoint allows a client to submit an email/password
    and receive a JWT token (and refresh token) 
    '''
    permission_classes = [permissions.AllowAny,]
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ValidationError as ex:
            raise ex
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