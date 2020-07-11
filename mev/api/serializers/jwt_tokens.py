from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, \
    TokenRefreshSerializer, \
    PasswordField

class AuthTokenSerializer(TokenObtainPairSerializer):
    '''
    Adds a couple fields onto the TokenObtainPairSerializer so that the 
    auto API documentation looks correct (e.g. takes a username/password and return
    a token+refresh token)
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(write_only=True)
        self.fields['password'] = PasswordField(write_only=True)
        self.fields['access'] = serializers.CharField(required=False, read_only=True)
        self.fields['refresh'] = serializers.CharField(required=False, read_only=True)

class RefreshAuthTokenSerializer(TokenRefreshSerializer):
    '''
    Adds on an access token so that the auto-generated API introspection 
    returns the proper fields.
    '''
    access = serializers.CharField(required=False, read_only=True)
