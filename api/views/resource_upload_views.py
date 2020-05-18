import uuid
import os

from django.conf import settings

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.response import Response

from api.serializers import UploadSerializer
import api.permissions as api_permissions

class ResourceUpload(APIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]

    permission_classes = [framework_permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UploadSerializer(data=request.data)
        if serializer.is_valid():
            print('was valid')
            print(request.data)
            try:
                owner = request.data['owner']
            except KeyError:
                owner = request.user
                print('owner was null, set to %s' % owner)

            resource_type = request.data.get('resource_type', None)

            upload = request.data['upload_file']
            tmp_path = os.path.join(
                settings.PENDING_FILES_DIR, 
                str(uuid.uuid4()))
            name = upload.name
            with open(tmp_path, 'wb+') as destination:
                for chunk in upload.chunks():
                    destination.write(chunk)
            return Response(status=status.HTTP_201_CREATED)
        else:
            print('was invalid')
            print(serializer.errors)


