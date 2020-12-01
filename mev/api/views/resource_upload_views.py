import uuid
import os
import logging

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from api.serializers.upload_serializer import UploadSerializer, DropboxUploadSerializer
from api.serializers.resource import ResourceSerializer
import api.permissions as api_permissions
from api.uploaders import ServerLocalUpload, DropboxLocalUpload, DropboxRemoteUpload
from api.async_tasks.uploaders import async_upload

User = get_user_model()

logger = logging.getLogger(__name__)

class ServerLocalResourceUpload(APIView):
    '''
    Endpoint for a direct upload to the server.
    '''
    parser_classes = [MultiPartParser]
    permission_classes = [framework_permissions.IsAuthenticated]
    serializer_class = UploadSerializer
    upload_handler_class = ServerLocalUpload

    def get_serializer(self):
        return self.serializer_class()

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, 
            context={'requesting_user': request.user})
        if serializer.is_valid():

            upload_handler = self.upload_handler_class()

            # get the file on the server:
            resource = upload_handler.handle_upload(request)

            # validate the resource, if applicable, and copy the file to 
            # the storage backend (async process, so response can return quickly)
            upload_handler.validate_and_store(resource)

            resource_serializer = ResourceSerializer(resource, context={'request': request})
            return Response(resource_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServerLocalResourceUploadProgress(APIView):
    '''
    Endpoint for checking the progress of an upload.

    Requests must contain a "X-Progress-ID" header to identify
    the upload they are monitoring.
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


class DropboxUpload(APIView):
    '''
    Endpoint for uploading resources from Dropbox

    Depending on the storage backend, the files will be uploaded locally
    or in the remote storage. Either way, the same endpoint is used.
    '''

    permission_classes = [framework_permissions.IsAuthenticated]
    serializer_class = DropboxUploadSerializer

    def get_serializer(self):
        return self.serializer_class()

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, 
            many=True,
            context={'requesting_user': request.user})

        if serializer.is_valid():

            data = serializer.data

            if settings.STORAGE_LOCATION == settings.LOCAL:
                uploader_name = DropboxLocalUpload.__name__
            elif settings.STORAGE_LOCATION == settings.REMOTE:
                uploader_name = DropboxRemoteUpload.__name__
            else:
                logger.error('Unrecognized storage location. This should not happen')
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # regardless of the ultimate location, we have the same interface to
            # upload the file(s)
            async_upload.delay(uploader_name, request.user.pk, data)
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


