from rest_framework import serializers

from django.contrib.auth import get_user_model

class UserSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name = 'user-detail')
    #workspaces = serializers.HyperlinkedRelatedField(view_name='workspace-detail', read_only=True, many=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            'url',
            'email',
            'password',
            #'workspaces'
        ]        