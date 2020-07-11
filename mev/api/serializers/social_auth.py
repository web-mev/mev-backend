from rest_framework import serializers

class SocialAuthTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
