from .api_root import ApiRoot
from .user_views import UserList, \
    UserDetail, \
    UserRegisterView, \
    PasswordResetView, \
    UserActivateView, \
    ResendActivationView
from .workspace_views import WorkspaceList, WorkspaceDetail
from .resource_views import ResourceList, ResourceDetail, ResourcePreview
from .workspace_resource_views import WorkspaceResourceList, WorkspaceResourceAdd
from .resource_upload_views import ResourceUpload, ResourceUploadProgress
from .resource_metadata import ResourceMetadataView