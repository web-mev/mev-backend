import logging
import mimetypes
import os

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.files.storage import default_storage

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from api.exceptions import NoResourceFoundException, \
    InactiveResourceException, \
    OwnershipException
from api.utilities.resource_utilities import check_resource_request_validity


logger = logging.getLogger(__name__)


class ResourceDownloadUrl(APIView):
    '''
    Request endpoint for obtaining a download URL.

    Depending on the storage backend, the file can be downloaded
    in different ways. This endpoint provides the link to that download.

    The reason for this alternative endpoint is that 302 redirects were 
    troublesome to handle on the frontend-- previous attempts to issue 302
    to a signed url (e.g. in bucket storage) caused the browser to load the 
    entire file as a Blob on the frontend. 

    This "workaround" will provide an appropriate URL in a JSON-format
    response payload. The browser can then decide how to deal with that url
    rather than relying on automatic redirects, etc. which are trickier to 
    manage.
    '''

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

        # If we are using remote/bucket storage, then django-storage 
        # will generate a signed URL
        url = r.datafile.url
        if not url:
            logger.error('Encountered a problem when preparing download for resource'
                ' with pk={u}'.format(u=resource_pk)
            )
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if settings.STORAGE_LOCATION == settings.LOCAL:
            download_url = request.build_absolute_uri(reverse('download-resource', kwargs={'pk': resource_pk}))
            download_type = 'local'
        else:
            download_url = url
            download_type = 'remote'
        
        # the 'download_type' is a flag for how the frontend should interpret the response.
        # For example, if it's a direct download from the local server, 
        # then it may choose to call the download url expecting a blob.
        return Response({'url': download_url, 'download_type': download_type})

class ResourceDownload(APIView):
    '''
    Request endpoint for downloading a file from local storage.

    We don't want to initiate these types of downloads for large files,
    so we limit the size.
    '''

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

        # if we don't have local storage, block this style of direct download
        if settings.STORAGE_LOCATION != settings.LOCAL:
            return Response(
                {'error': 'The server configuration prevents direct server downloads.'}, 
                status=status.HTTP_400_BAD_REQUEST)

        # requester can access, resource is active. OK so far.
        # Check the file size. We don't want large files tying up the server
        # Those should be performed by something else, like via Dropbox.
        # HOWEVER, this is only an issue if the storage backend is local. 
        # Redirects for bucket storage can obviously be handled since they are 
        # downloading directly from the bucket and this will not tie up our server.
        size_in_bytes = r.datafile.size
        if size_in_bytes > settings.MAX_DOWNLOAD_SIZE_BYTES:
            msg = ('The resource size exceeds our limits for a direct'
                ' download. Please use one of the alternative download methods'
                ' more suited for larger files.')
            return Response(
                {'size': msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        if default_storage.exists(r.datafile.name):
            contents = r.datafile.open('rb')
            mime_type, _ = mimetypes.guess_type(r.datafile.name)
            response = HttpResponse(content = contents)
            response['Content-Type'] = mime_type
            response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(r.name)
            return response
        else:
            logger.error(f'Local storage was specified, but the resource at path {r.datafile.path}'
                ' was not found.')
            return Response(status = status.HTTP_500_INTERNAL_SERVER_ERROR)
