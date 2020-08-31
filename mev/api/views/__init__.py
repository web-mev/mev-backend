from .api_root import ApiRoot
from .user_views import UserList, \
    UserDetail, \
    UserRegisterView, \
    PasswordResetView, \
    PasswordResetConfirmView, \
    UserActivateView, \
    ResendActivationView, \
    PasswordChangeView
from .social_views import GoogleOauth2View
from .workspace_views import WorkspaceList, WorkspaceDetail
from .resource_views import ResourceList, ResourceDetail, ResourcePreview
from .workspace_resource_views import WorkspaceResourceList, WorkspaceResourceAdd
from .resource_upload_views import ServerLocalResourceUpload, ServerLocalResourceUploadProgress
from .resource_metadata import ResourceMetadataView, \
    ResourceMetadataObservationsView, \
    ResourceMetadataFeaturesView, \
    ResourceMetadataParentOperationView
from .token_views import TokenObtainView, RefreshTokenView
from .resource_type_views import ResourceTypeList
from .operation_views import OperationList, OperationDetail, OperationCreate

def sentry_debug(request):
    '''
    A function guaranteed to raise an exception to 
    test that we have configured Sentry correctly
    and it is receiving exceptions.
    '''
    bad_op = 1/0