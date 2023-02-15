import random
import hashlib
import string
import time
import json
import logging

import globus_sdk
from globus_sdk import TransferAPIError, \
    GlobusAPIError

from django.conf import settings
from django.core.files.storage import default_storage

from exceptions import NonexistentGlobusTokenException
from api.models import GlobusTokens, GlobusTask
from api.utilities.admin_utils import alert_admins
from api.storage import S3_PREFIX

logger = logging.getLogger(__name__)

GLOBUS_UPLOAD = '__globus_upload__'
GLOBUS_DOWNLOAD = '__globus_download__'


def random_string(length=12):
    '''
    Used to generate a state parameter for the OAuth2 flow
    with Globus Auth
    '''
    ALLOWED_CHARS = string.ascii_letters + string.digits
    # Implementation borrowed from python social auth pkg
    try:
        random.SystemRandom()
    except NotImplementedError:
        try:
            key = settings.SECRET_KEY
        except AttributeError:
            key = ''
        seed = f'{random.getstate()}{time.time()}{key}'
        random.seed(hashlib.sha256(seed.encode()).digest())
    return ''.join([random.choice(ALLOWED_CHARS) for i in range(length)])


def get_globus_client():
    return globus_sdk.ConfidentialAppAuthClient(
        settings.GLOBUS_CLIENT_ID,
        settings.GLOBUS_CLIENT_SECRET
    )


def create_token(user, token_dict):
    GlobusTokens.objects.create(
        user=user,
        tokens=token_dict
    )


def create_or_update_token(user, token_dict):
    logger.info(f'Create or update token for user {user.email}'
                f' with token info: {token_dict}')
    try:
        logger.info('Try to update the token')
        update_tokens_in_db(user, token_dict)
    except NonexistentGlobusTokenException:
        logger.info('Token did not exist. Create a new one.')
        create_token(user, token_dict)


def get_globus_token_from_db(user, existence_required=True):
    '''
    Returns a GlobusTokens instance (our database model)
    '''
    logger.info(f'Get Globus token for user {user}')
    try:
        return GlobusTokens.objects.get(user=user)
    except GlobusTokens.DoesNotExist:
        logger.info('No tokens for this user')
        if existence_required:
            logger.info('Required there to be an existing token,'
                        f' but none was found for user {user}')
            raise NonexistentGlobusTokenException()
        return None


def get_globus_tokens(user, key=None):
    '''
    Returns the Globus token for the appropriate resource server
    specified by `key`. If `key` is None, return the entire dict,
    which will, in general, have multiple resource servers such 
    as:
    {
        "auth.globus.org": {
            "scope": "profile email openid",
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_at_seconds": 1659645740,
            "resource_server": "auth.globus.org"
        },
        "transfer.api.globus.org": {
            "scope": "urn:globus:auth:scope:transfer.api.globus.org:all",
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_at_seconds": 1659645740,
            "resource_server": "transfer.api.globus.org"
        }
    }
    '''
    gt = get_globus_token_from_db(user)
    tokens = gt.tokens

    if key is None:
        return tokens
    elif key in tokens:
        return tokens[key]
    else:
        raise Exception(f'Unknown key {key} requested in Globus token.'
                  f' Available keys are {tokens.keys()}')


def get_globus_uuid(user):
    '''
    Returns the Globus identifier for the given
    WebMeV user
    '''
    auth_tokens = get_globus_tokens(user, key='auth.globus.org')
    client = get_globus_client()
    introspection_data = perform_token_introspection(client, auth_tokens)
    return introspection_data['sub']


def create_application_transfer_client():
    '''
    Given a WebMeV user, create/return a globus_sdk.TransferClient that 
    is associated with our application. Note that this client does NOT
    use the tokens for the user who is transferring data. This client is used, 
    for instance, to set ACLs on the Globus Collection we own/control
    '''

    client = get_globus_client()
    cc_authorizer = globus_sdk.ClientCredentialsAuthorizer(
        client, settings.GLOBUS_TRANSFER_SCOPE)
    return globus_sdk.TransferClient(authorizer=cc_authorizer)


def create_user_transfer_client(user):
    '''
    Given a WebMeV user, create/return a globus_sdk.TransferClient
    '''
    logger.info(f'Create a TransferClient for the user {user}.')

    transfer_tokens = get_globus_tokens(user, 'transfer.api.globus.org')

    client = get_globus_client()

    # just so we get the log to see what this token looks like for debugging:
    _ = perform_token_introspection(client, transfer_tokens)

    # create another authorizer using the tokens for the transfer API
    transfer_rt_authorizer = globus_sdk.RefreshTokenAuthorizer(
        transfer_tokens['refresh_token'],
        client,
        access_token=transfer_tokens['access_token'],
        expires_at=transfer_tokens['expires_at_seconds']
    )
    return globus_sdk.TransferClient(authorizer=transfer_rt_authorizer)


def refresh_globus_token(client, token):
    '''
    Performs a token refresh and returns a dict with the 
    updated token info.

    For example, a response might look like:
    {
        "transfer.api.globus.org": {
            "scope": "urn:globus:auth:scope:transfer.api.globus.org:all",
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_at_seconds": 1659654653,
            "resource_server": "transfer.api.globus.org"
        }
    }
    '''
    try:
        token_refresh_response = client.oauth2_refresh_token(
            token['refresh_token'])
        if token_refresh_response.http_status == 200:
            return token_refresh_response.by_resource_server
        else:
            err_msg = ('Encountered an issue refreshing token.'
                f' Status code: {token_refresh_response.http_status}.\n'
                f' Text: {token_refresh_response.text}'
            )
            logger.info(err_msg)
            alert_admins(err_msg)
            return None
    except globus_sdk.services.auth.errors.AuthAPIError as ex:
        status_code = ex.http_status
        message = ex.message
        err_msg = ('Encountered error with Globus token refresh.'
            f' Code was {status_code}\nMessage was: {message}'
        )
        logger.info(err_msg)
        alert_admins(err_msg)
        return None


def get_active_token(client, token, resource_server):
    '''
    Given the current token (e.g. for auth.globus.org or transfer), 
    check if active.

    If not, refresh.

    Either way, this function returns an active token (a dict)
    '''
    response = client.oauth2_validate_token(token['access_token'])

    # This section establishes whether the token itself is still active.
    # This is separate from any session refreshes we might need to perform
    if response.data['active']:
        logger.info('Token was active.')
        return token
    else:
        logger.info('Token was not active. Go refresh.')
        refreshed_token_dict = refresh_globus_token(client, token)
        if refreshed_token_dict is not None:
            return refreshed_token_dict[resource_server]
        return None
        

def update_tokens_in_db(user, updated_tokens):
    '''
    Updates the tokens for this user.
    '''
    logger.info(f'Update the token for user {user}')
    gt = get_globus_token_from_db(user)
    gt.tokens = updated_tokens
    gt.save()


def perform_token_introspection(client, token):
    introspection_data = client.oauth2_token_introspect(
        token['access_token'],
        include='session_info')
    logger.info('Token data from introspect:\n'
                f'{json.dumps(introspection_data.data, indent=2)}')
    return introspection_data.data


def session_is_recent(client, auth_token):
    '''
    Check if the most recent session authentication was within
    the time limit. Returns a bool indicating whether the user
    has recently authenticated (True) or whether it is too old
    (False)
    '''
    logger.info(f'Check for session with:{json.dumps(auth_token, indent=2)}')

    introspection_data = perform_token_introspection(client, auth_token)

    user_id = introspection_data['sub']
    authentications_dict = introspection_data['session_info']['authentications']
    logger.info(f'Globus auths:\n{json.dumps(authentications_dict, indent=2)}')
    if user_id in authentications_dict:
        # in seconds since epoch
        auth_time = authentications_dict[user_id]['auth_time']
        # how many minutes have passed PLUS some buffer
        time_delta = (time.time() - auth_time)/60 + 5
        logger.info(f'Time delta was: {time_delta}')
        if time_delta > settings.GLOBUS_REAUTHENTICATION_WINDOW_IN_MINUTES:
            logger.info('Most recent session was too old.')
            return False
        logger.info('Most recent session was within the limit.')
        return True
    logger.info('No session authentications found.')
    return False


def check_globus_tokens(user):
    '''
    Checks that the tokens for this user are valid.

    Note that we maintain two sets of tokens for:
    - auth.globus.org
    - transfer.api.globus.org

    We ensure that both are valid and update as necessary.
    '''

    '''
    all_tokens is a dict and looks like
    {
        "auth.globus.org": {
            "scope": "profile email openid",
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_at_seconds": 1659645740,
            "resource_server": "auth.globus.org"
        },
        "transfer.api.globus.org": {
            "scope": "urn:globus:auth:scope:transfer.api.globus.org:all",
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_at_seconds": 1659645740,
            "resource_server": "transfer.api.globus.org"
        }
    }
    '''
    all_tokens = get_globus_tokens(user)
    client = get_globus_client()
    updated_tokens = {}
    update_failed = False
    for resource_server in all_tokens.keys():
        d = get_active_token(
            client,
            all_tokens[resource_server],
            resource_server
        )
        if d is not None:
            updated_tokens[resource_server] = d
        else:
            logger.info('Failed to update or get active tokens for Globus.')
            update_failed = True
            break # if a token was not active, break the for loop

    if update_failed:
        # at least one of the token updates failed. We don't update the 
        # database and return False to indicate we don't have a recent session.
        # This is likely the most conservative route if one of the token
        # updates fails.
        return False
    else:
        update_tokens_in_db(user, updated_tokens)

        # At this point we have an active token. However, we still need to
        # ensure we have a recent session. The high-assurance storage on S3
        # requires a relatively recent session authentication.
        return session_is_recent(client, updated_tokens['auth.globus.org'])


def add_acl_rule(transfer_client, globus_user_uuid, folder, permissions):
    '''
    Calls the Globus API to add an access rule so that the WebMeV
    user's data can be transferred into our Globus shared collection.
    Returns the rule ID, which allows us to revoke once the transfer is 
    complete.
    '''
    rule_data = {
        "DATA_TYPE": "access",
        "principal_type": "identity",
        "principal": globus_user_uuid,
        "path": folder,
        "permissions": permissions,
    }
    try:
        result = transfer_client.add_endpoint_acl_rule(
            settings.GLOBUS_ENDPOINT_ID, rule_data)
        logger.info(f'ACL add result is:\n{result}')
        if result.http_status == 201:
            return result['access_id']
        else:
            logger.info('Failed to add ACL rule.')
            return None
    except GlobusAPIError as ex:
        logger.info(f'Failed to add ACL rule. Exception was {ex}')
        return None


def delete_acl_rule(rule_id):
    app_transfer_client = create_application_transfer_client()
    logger.info(f'Remove endpoint rule {rule_id}')
    try:
        result = app_transfer_client.delete_endpoint_acl_rule(
            settings.GLOBUS_ENDPOINT_ID, rule_id)
        logger.info(f'Rule removal result {result}')
        if result.http_status == 200:
            return True
        else:
            logger.info('ACL rule was not deleted.')
            return False
    except GlobusAPIError as ex:
        logger.info(f'Failed to remove ACL rule. Exception was {ex}')
        return False


def submit_transfer(transfer_client, transfer_data):

    task_id = None
    try:
        task_id = transfer_client.submit_transfer(transfer_data)['task_id']
    except TransferAPIError as ex:
        authz_params = ex.info.authorization_parameters
        if not authz_params:
            err_msg = f'Exception with initiating Globus transfer: {ex}'
        else:
            err_msg = f'Error with initiating Globus transfer. Got auth params: {authz_params}'
        logger.info(err_msg)
        alert_admins(err_msg)
    except GlobusAPIError as ex:
        err_msg = f'Caught a general GlobusAPIError. Exception was {ex}'
        logger.info(err_msg)
        alert_admins(err_msg)
    return task_id


def post_upload(transfer_client, task_id, user):
    '''
    Handles the post-upload behavior following a Globus transfer
    where the files are transferred TO WebMeV. 
    '''

    # Copy the files from the Globus bucket to our WebMeV storage
    # TODO: Use the endpoint manager client here?
    for info in transfer_client.task_successful_transfers(task_id):
        # this is relative to the Globus bucket
        rel_path = info['destination_path']
        path = f'{S3_PREFIX}{settings.GLOBUS_BUCKET}{rel_path}'
        # Note that even if Globus says the transfer is complete,
        # we can have a race condition where the copy does not work
        # since boto3 can't (yet) locate the source object. Thus,
        # we wait before attempting the copy
        default_storage.wait_until_exists(path)
        default_storage.create_resource_from_interbucket_copy(
            user,
            path
        )
    
    #TODO: handle transfer failures
