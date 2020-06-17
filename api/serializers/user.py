import logging

from rest_framework import serializers
from rest_framework.exceptions import APIException

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from api.utilities.basic_utils import decode_uid

logger = logging.getLogger(__name__)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name = 'user-detail')
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
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
                user = User.objects.create_user(
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

class ResendActivationSerializer(serializers.Serializer):
    '''
    If the user's token expires (the one sent in the email),
    they can request a new activation link by supplying their email
    '''
    email = serializers.EmailField()

    def validate(self, data):
        # validate the input from the DRF serializer class
        validated_data = super().validate(data)
        try:
            self.user = User.objects.get(email=validated_data['email'])
            return validated_data
        except User.DoesNotExist:
            raise ValidationError({'email': 'Unknown user.'})


class UserActivateSerializer(serializers.Serializer):
    '''
    This handles the request to activate a user once they have
    clicked on a link in their email.
    '''
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, data):
        # validate the input from the DRF serializer class
        validated_data = super().validate(data)
        try:
            uid = decode_uid(validated_data.get('uid', ''))
        except Exception as ex:

            raise ValidationError({'uid': 'Could not decode the UID field.'})

        token = validated_data.get('token', '')

        try:
            self.user = User.objects.get(pk=uid)

            # if the user is already active (e.g. from clicking on the
            # same link), we don't need to go further.
            if self.user.is_active:
                return validated_data
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise ValidationError(
                {'uid': 'Invalid UID'}
            )
        token_is_valid = default_token_generator.check_token(self.user, token)
        if token_is_valid:
            return validated_data
        else:
            raise ValidationError(
                {'token': 'Invalid token'}
            )

class PasswordResetSerializer(serializers.Serializer):
    
    email = serializers.EmailField()