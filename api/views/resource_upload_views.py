import uuid
import os

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.response import Response

from api.serializers import UploadSerializer, ResourceSerializer
import api.permissions as api_permissions
import api.async_tasks as api_tasks
from api.utilities.resource_utilities import create_resource_from_upload

User = get_user_model()

class ResourceUpload(APIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]

    permission_classes = [framework_permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UploadSerializer(data=request.data)
        if serializer.is_valid():

            # the owner key is optional.  If not specified,
            # the uploaded resource will be assigned to the 
            # user originating this request.
            try:
                owner_email = request.data['owner_email']
                try:
                    owner = User.objects.get(email=owner_email)
                except User.DoesNotExist:
                    return Response(
                        {'owner_email': 'Owner email not found.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except KeyError:
                owner = request.user

            # The resource type is required and enforced by the 
            # serializer.
            resource_type = request.data.get('resource_type')
            upload = request.data['upload_file']
            filename = upload.name
            tmp_path = os.path.join(
                settings.PENDING_FILES_DIR, 
                str(uuid.uuid4()))
            with open(tmp_path, 'wb+') as destination:
                for chunk in upload.chunks():
                    destination.write(chunk)

            # create a Resource instance:
            resource = create_resource_from_upload(
                tmp_path, 
                filename, 
                resource_type, 
                owner
            )

            # now that we have the file, start the validation process
            # in the background
            api_tasks.validate_resource.delay(resource.pk)
            resource_serializer = ResourceSerializer(resource, context={'request': request})
            return Response(resource_serializer.data, status=status.HTTP_201_CREATED)
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


