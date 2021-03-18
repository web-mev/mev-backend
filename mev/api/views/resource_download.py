import logging
import mimetypes
import os

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework import permissions as framework_permissions
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from api.models import Resource
from api.exceptions import NoResourceFoundException, \
    InactiveResourceException, \
    OwnershipException
from api.utilities.resource_utilities import check_resource_request_validity
from api.storage_backends import get_storage_backend

logger = logging.getLogger(__name__)

class ResourceDownload(APIView):
    '''
    Request endpoint for downloading a file.

    We don't want to initiate these types of downloads for large files,
    so we limit the size.
    '''

    permission_classes = [framework_permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        resource_pk=kwargs['pk']
        try:
            r = check_resource_request_validity(user, resource_pk)
        except NoResourceFoundException:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except InactiveResourceException:
            return Response(
                {'error': 'The resource is inactive.'}, 
                status=status.HTTP_400_BAD_REQUEST)
        except OwnershipException:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # requester can access, resource is active. OK so far.
        # Check the file size. We don't want large files tying up the server
        # Those should be performed by something else, like via Dropbox.
        size_in_bytes = r.size
        if size_in_bytes > settings.MAX_DOWNLOAD_SIZE_BYTES:
            msg = ('The resource size exceeds our limits for a direct'
                ' download. Please use one of the alternative download methods'
                ' more suited for larger files.')
            return Response(
                {'size': msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # size is acceptable.
        # Now, depending on the storage backend, we return different things.
        # If we have local storage, we just return the file contents.
        # If we have remote storage, we return a signed url and issue a 302 to redirect them

        # url can be a local path or a remote url depending on the storage backend we are using
        storage_backend = get_storage_backend()
        url = storage_backend.get_download_url(r)

        if not url:
            logger.error('Encountered a problem when preparing download for resource'
                ' with pk={u}'.format(u=resource_pk)
            )
            return Response(status=status.HTTP_500_SERVER_ERROR)

        if storage_backend.is_local_storage:
            if os.path.exists(url):
                contents = open(url, 'rb')
                mime_type, _ = mimetypes.guess_type(url)
                response = HttpResponse(content = contents)
                response['Content-Type'] = mime_type
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(url)
                return response
            else:
                logger.error('Local storage was specified, but the resource at path {p}'
                    ' was not found.'.format(p=url))
                return Response(status = status.HTTP_500_SERVER_ERROR)
        else:
            return HttpResponseRedirect(url)