import logging

from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, \
    TokenRefreshView

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
        return super().post(request, *args, **kwargs)


class RefreshTokenView(TokenRefreshView):
    '''
    Endpoint for refreshing the JWT auth token.
    '''
    serializer_class = RefreshAuthTokenSerializer