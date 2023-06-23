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

class PasswordSerializer(serializers.Serializer):
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

class UserRegisterSerializer(PasswordSerializer):
    '''
    Used when registering a user by email and password
    '''

    email = serializers.EmailField() 
    
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


class UidAndTokenSerializer(serializers.Serializer):
    '''
    This handles payloads where a request includes a UID and token
    such as for resetting passwords or activating registration
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

class UserActivateSerializer(UidAndTokenSerializer):
    '''
    This handles the request to activate a user once they have
    clicked on a link in their email.
    '''

    def validate(self, data):
        # validate the UID and token in the parent class
        return super().validate(data)


class PasswordResetSerializer(serializers.Serializer):
    
    email = serializers.EmailField()

    def validate(self, data):
        # validate the input from the DRF serializer class
        validated_data = super().validate(data)

        try:
            self.user = User.objects.get(email=validated_data['email'])
            if self.user.has_usable_password():
                return validated_data
            else:
                raise ValidationError({'email': 'Cannot reset password for this user.'
                    ' This can happen if you have used an alternative registration method'
                    ' that did not require an email/password.'})
        except User.DoesNotExist:
            raise ValidationError({'email': 'Unknown user.'})

class PasswordResetConfirmSerializer(UidAndTokenSerializer, PasswordSerializer):
    '''
    This handles the reset the users's password
    oncce they have clicked on a link in their email.
    '''

    def validate(self, data):
        validated_data = PasswordSerializer.validate(self, data)
        validated_data = UidAndTokenSerializer.validate(self, validated_data)
        return validated_data

class PasswordChangeSerializer(PasswordSerializer):
    '''
    This handles the reset the users's password
    once they have clicked on a link in their email.
    '''
    current_password = serializers.CharField(write_only=True) 

    def validate(self, data):
        user = self.context['request'].user
        if not user.has_usable_password():
            raise ValidationError({'current_password': 'You most likely have'
                ' authenticated using a third-party identity provider.'
                ' Therefore, your WebMeV account does not have an'
                ' associated password.'})
        # the user is authenticated, so the request had some authentication token
        is_password_valid = self.context['request'].user.check_password(data['current_password'])
        if not is_password_valid:
            raise ValidationError({'current_password': 'The current password was not valid.'})
        validated_data = PasswordSerializer.validate(self, data)
        return validated_data
