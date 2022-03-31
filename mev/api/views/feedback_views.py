from rest_framework import permissions as framework_permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.serializers.feedback import FeedbackSerializer
from api.models import FeedbackMessage
from api.utilities.basic_utils import alert_admins

class SubmitFeedbackView(APIView):

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def get(self, request, format=None):
        if request.user.is_staff:
            messages = FeedbackMessage.objects.all()
            serializer = FeedbackSerializer(messages, many=True)
            return Response(serializer.data)
        else:
            raise PermissionDenied()

    def post(self, request, format=None):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            data = serializer.data
            alert_admins(data['message'])
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)