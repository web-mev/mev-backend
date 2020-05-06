from django.urls import path

import api.views

urlpatterns = [
    path('workspaces/', api.views.WorkspaceList.as_view(), name='workspace-list'),
    path('workspaces/<uuid:pk>/', api.views.WorkspaceDetail.as_view(), name='workspace-detail'),
    path('users/', api.views.UserList.as_view(), name='user-list'),
    path('users/<int:pk>/', api.views.UserDetail.as_view(), name='user-detail'),
    path('', api.views.ApiRoot.as_view(), name='api-root')
]
