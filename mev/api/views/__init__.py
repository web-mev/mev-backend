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
from .resource_metadata import ResourceMetadataView