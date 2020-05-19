import uuid
import os

from django.conf import settings
from django.core.cache import cache

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
            try:
                owner = request.data['owner']
            except KeyError:
                owner = request.user
            resource_type = request.data.get('resource_type', None)

            upload = request.data['upload_file']
            tmp_path = os.path.join(
                settings.PENDING_FILES_DIR, 
                str(uuid.uuid4()))
            name = upload.name
            with open(tmp_path, 'wb+') as destination:
                for chunk in upload.chunks():
                    destination.write(chunk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResourceUploadProgress(APIView):
    '''
    Endpoint for checking the progress of an upload
    '''
    def get(self, request, format=None):
        progress_id = None
        if 'HTTP_X_PROGRESS_ID' in self.request.GET :
            progress_id = request.GET['HTTP_X_PROGRESS_ID']
        elif 'HTTP_X_PROGRESS_ID' in request.META:
            progress_id = request.META['HTTP_X_PROGRESS_ID']
        if progress_id:
            cache_key = "%s_%s" % (
                request.META['REMOTE_ADDR'], progress_id
            )
            data = cache.get(cache_key)
            return Response(data)
        else:
            error_msg = ('Requests must include a "X-Progress-ID" key'
            ' in the header or as a query parameter with the GET request')
            return Response({'errors': error_msg}, status=status.HTTP_400_BAD_REQUEST)


