import uuid
import os
import re
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions as framework_permissions
from rest_framework import status

from django.conf import settings

import globus_sdk
from globus_sdk import TransferAPIError, \
    GlobusAPIError

from exceptions import NoResourceFoundException

from api.utilities.globus import random_string, \
    get_globus_client, \
    create_or_update_token, \
    get_globus_token_from_db, \
    get_globus_uuid, \
    check_globus_tokens, \
    create_user_transfer_client, \
    create_application_transfer_client, \
    add_acl_rule, \
    submit_transfer, \
    GLOBUS_UPLOAD
from api.utilities.admin_utils import alert_admins
from api.utilities.resource_utilities import get_resource_by_pk
from api.async_tasks.globus_tasks import poll_globus_task, \
    perform_globus_download
from api.models import GlobusTask, GlobusTask

SESSION_MESSAGE = ('Since this is a high-assurance Globus collection, we'
                   ' require a recent authentication. Please sign-in again.'
                   )

logger = logging.getLogger(__name__)


class GlobusTransferList(APIView):

    def get(self, request, *args, **kwargs):
        '''
        Returns a list of active (incomplete) Globus tasks.
        '''
        tasks = GlobusTask.objects.filter(
            user=request.user, transfer_complete=False)
        task_info = []
        for t in tasks:
            task_info.append(
                {
                    'label': t.label,
                    'task_id': t.task_id
                }
            )
        return Response(task_info)


class GlobusUploadView(APIView):

    permission_classes = [
        framework_permissions.IsAuthenticated
    ]

    def post(self, request, *args, **kwargs):
        '''
        request.data looks like:
        {
            'params': {
                'label': '<LABEL>', 
                'endpoint': '<legacy id>#<uploader's endpont UUID>', 
                'path': '<source path/dir>', 
                'endpoint_id': '<source endpoint UUID>', 
                'entity_type': 'GCP_mapped_collection', 
                'high_assurance': 'false', 
                'file[0]': '<FILENAME>', 
                'file[1]': '<FILENAME>', 
                'action': 'http://localhost:4200/globus/upload-redirect/', 
                'method': 'GET'
            }
        }
        Note that the actual files are given as file[0], file[1],...
        up to the N-1 files requested.
        '''
        if not settings.GLOBUS_ENABLED:
            return Response('Globus was not configured', 
                            status=status.HTTP_400_BAD_REQUEST)
                            
        params = request.data['params']

        app_transfer_client = create_application_transfer_client()
        user_transfer_client = create_user_transfer_client(request.user)

        user_uuid = get_globus_uuid(request.user)

        # This is a temporary folder within the Globus shared collection
        tmp_folder = f'/tmp-{uuid.uuid4()}/'

        # Create the rule and add it to the Globus shared collection
        rule_id = add_acl_rule(
            app_transfer_client, user_uuid, tmp_folder, 'rw')
        if rule_id is None:
            alert_admins('Failed to add ACL rule. See logs.')
            return Response(
                {'message': 'Unable to upload. An administrator has been notified'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Now onto the business of initiating the transfer
        source_endpoint_id = params['endpoint_id']
        destination_endpoint_id = settings.GLOBUS_ENDPOINT_ID
        transfer_data = globus_sdk.TransferData(
            transfer_client=user_transfer_client,
            source_endpoint=source_endpoint_id,
            destination_endpoint=destination_endpoint_id,
            label=params['label'])

        file_keys = [x for x in params.keys() \
            if re.fullmatch('file\[\d+\]', x)]
        for k in file_keys:
            source_path = os.path.join(
                params['path'],
                params[k]
            )
            destination_path = os.path.join(
                tmp_folder,
                params[k]
            )
            transfer_data.add_item(
                source_path=source_path,
                destination_path=destination_path
            )

        user_transfer_client.endpoint_autoactivate(source_endpoint_id)
        user_transfer_client.endpoint_autoactivate(destination_endpoint_id)
        task_id = submit_transfer(user_transfer_client, transfer_data)
        if task_id:
            task_data = user_transfer_client.get_task(task_id)
            GlobusTask.objects.create(
                user=request.user,
                task_id=task_id,
                rule_id=rule_id,
                label=task_data['label']
            )
            poll_globus_task.delay(task_id, GLOBUS_UPLOAD)
        return Response({'transfer_id': task_id})


class GlobusDownloadView(APIView):

    permission_classes = [
        framework_permissions.IsAuthenticated 
    ]  

    def post(self, request, *args, **kwargs):

        logger.info('Requesting download of data to Globus with'
            f' data={request.data}')

        # before starting a potentially long async call, check that the
        # provided resource PKs are fine
        requested_pks = [uuid.UUID(x) for x in request.data['pk_set']]
        resource_set = set()
        for pk in requested_pks:
            try:
                resource_set.add(get_resource_by_pk(pk))
            except NoResourceFoundException:
                return Response(f'Could not locate resource with pk={pk}', 
                    status=status.HTTP_404_NOT_FOUND)        

        perform_globus_download.delay(requested_pks,
            request.user.pk, request.data)
        return Response(status=status.HTTP_200_OK)


class GlobusInitiate(APIView):

    def return_globus_browser_url(self, direction, request_origin):

        if direction == 'upload':
            callback = settings.GLOBUS_UPLOAD_REDIRECT_URI.format(
                origin=request_origin
            )
            upload_uri = settings.GLOBUS_BROWSER_UPLOAD_URI.format(callback=callback)
            return Response({
                'globus-browser-url': upload_uri
            })
        elif direction == 'download':
            callback = settings.GLOBUS_DOWNLOAD_REDIRECT_URI.format(
                origin=request_origin
            )
            download_uri = settings.GLOBUS_BROWSER_DOWNLOAD_URI.format(callback=callback)
            return Response({
                'globus-browser-url': download_uri
            })
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def handle_session_condition(self, client, user, upload_or_download_state, request_origin):
        '''
        Even if we have valid Globus tokens, we can enounter situations where the session
        is too old. If that is the case, we have to redirect the user to reauthenticate.
        '''
        has_recent_globus_session = check_globus_tokens(user)
        if has_recent_globus_session:
            logger.info(
                'Had recent globus token/session. Go to Globus file browser')
            return self.return_globus_browser_url(upload_or_download_state, request_origin)
        else:
            logger.info(
                'Did not have a recent authentication/session. Send to Globus auth.')
            globus_user_uuid = get_globus_uuid(user)
            additional_authorize_params = {}
            additional_authorize_params['state'] = random_string()
            additional_authorize_params['session_required_identities'] = globus_user_uuid
            additional_authorize_params['prompt'] = 'login'
            additional_authorize_params['session_message'] = SESSION_MESSAGE
            auth_uri = client.oauth2_get_authorize_url(
                query_params=additional_authorize_params)
            return Response({
                'globus-auth-url': auth_uri
            })

    def get(self, request, *args, **kwargs):

        if not settings.GLOBUS_ENABLED:
            return Response('Globus was not configured', 
                            status=status.HTTP_400_BAD_REQUEST)

        request_origin = request.META['HTTP_ORIGIN']
        client = get_globus_client()
        client.oauth2_start_flow(
            settings.GLOBUS_AUTH_REDIRECT_URI.format(origin=request_origin),
            refresh_tokens=True,
            requested_scopes=settings.GLOBUS_SCOPES
        )
        logger.info(f'Query params: {request.query_params}')
        upload_or_download_state = request.query_params.get('direction')

        if 'code' in request.query_params:
            # If here, returning from the Globus auth with a code
            code = request.query_params.get('code', '')
            tokens = client.oauth2_exchange_code_for_tokens(code)
            rt = tokens.by_resource_server
            # rt looks like (a native python dict):
            # {
            #     'auth.globus.org': {
            #         'scope': 'email openid profile',
            #         'access_token': '<TOKEN>',
            #         'refresh_token': '<token>',
            #         'token_type': 'Bearer',
            #         'expires_at_seconds': 1649953535,
            #         'resource_server': 'auth.globus.org'

            #     },
            #     'transfer.api.globus.org': {
            #         'scope': 'urn:globus:auth:scope:transfer.api.globus.org:all',
            #         'access_token': '<TOKEN>',
            #         'refresh_token': '<TOKEN>',
            #         'token_type': 'Bearer',
            #         'expires_at_seconds': 1649953535,
            #         'resource_server': 'transfer.api.globus.org'
            #     }
            # }
            create_or_update_token(request.user, rt)
            return self.handle_session_condition(client, 
                request.user, upload_or_download_state, request_origin)
        else:
            logger.info('No "code" present in request params')
            # no 'code'. This means we are not receiving
            # a 'callback' from globus auth.

            # this will be None if the current user does not have Globus tokens
            existing_globus_tokens = get_globus_token_from_db(
                request.user, existence_required=False)

            if existing_globus_tokens:
                logger.info('Had existing globus tokens for this user')
                return self.handle_session_condition(client, 
                    request.user, upload_or_download_state, request_origin)
            else:
                logger.info(
                    'did NOT have existing globus tokens for this user. Init oauth2')
                # existing_globus_tokens was None, so we need to
                # initiate the start of the oauth2 flow.
                additional_authorize_params = {}
                additional_authorize_params['state'] = random_string()
                if request.query_params.get('signup'):
                    additional_authorize_params['signup'] = 1
                auth_uri = client.oauth2_get_authorize_url(
                    query_params=additional_authorize_params)
                logger.info(f'Auth uri: {auth_uri}')
                return Response({
                    'globus-auth-url': auth_uri
                })
