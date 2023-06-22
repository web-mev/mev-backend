from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser

from api.models import Message
from api.serializers.message import MessageSerializer


class MessageList(generics.ListAPIView):
    '''
    Lists all available Message instances and exposes
    creation interface
    '''
    permission_classes = [AllowAny]
    serializer_class = MessageSerializer
    queryset = Message.objects.all()


class MessageCreate(generics.CreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = MessageSerializer


class LatestMessage(APIView):

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        '''
        Returns the most recent message
        '''
        try:
            m = Message.objects.latest('creation_datetime')
            serializer = MessageSerializer(m, many=False)
            return Response(serializer.data)
        except Message.DoesNotExist:
            return Response({})