from rest_framework import serializers

class SocialAuthTokenSerializer(serializers.Serializer):
    provider_token = serializers.CharField(write_only=True)
    access = serializers.CharField(required=False, read_only=True)
    refresh = serializers.CharField(required=False, read_only=True)
