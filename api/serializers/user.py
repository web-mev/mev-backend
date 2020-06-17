import logging

from rest_framework import serializers
from rest_framework.exceptions import APIException

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name = 'user-detail')
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            'url',
            'email',
            'password'
        ]        


class UserRegisterSerializer(serializers.Serializer):
    '''
    Used when registering a user by email and password
    '''

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)    
    confirm_password = serializers.CharField(write_only=True) 

    def validate(self, data):
        '''
        Checks that the password is "reasonable"
        and that the re-typed password matches.
        '''
        password = data['password']
        try:
            validate_password(password)
        except ValidationError as ex:
            serializer_error = serializers.as_serializer_error(ex)
            raise serializers.ValidationError(
                {"password": serializer_error["non_field_errors"]}
            )
        confirm_password = data['confirm_password']
        if confirm_password != password:
            raise serializers.ValidationError({'confirm_password':
                'The passwords do not match. Please try again.'
            })
        
        return data
    
    def create(self, validated_data):
        try:
            with transaction.atomic():
                logger.info('About to create database user for'
                    ' email {email}'.format(
                        email=validated_data['email']
                    ))
                user = get_user_model().objects.create_user(
                    validated_data['email'], 
                    validated_data['password'],
                    is_active=False)
                return user
                
        except Exception as ex:
            logger.error('User ({email}) could not be created due'
                ' to: {ex}'.format(
                    email=validated_data['email'],
                    ex=ex
                ))
            raise APIException('Could not register user.')


class PasswordResetSerializer(serializers.Serializer):
    
    email = serializers.EmailField()