from rest_framework import serializers

from api.models import FeedbackMessage

class FeedbackSerializer(serializers.ModelSerializer):

    user_email = serializers.EmailField(source='user.email', required=False)
    timestamp = serializers.DateTimeField(
        source='message_datetime', 
        read_only=True
    )
    class Meta:
        model = FeedbackMessage
        fields = [
            'message',
            'user_email',
            'timestamp'
        ]
