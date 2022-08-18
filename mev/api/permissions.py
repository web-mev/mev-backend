from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    '''
    The purpose of this permission class is to limit 
    viewing or editing of resources to the owner

    Assumes the instance `obj` has an `owner` attribute
    '''

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsInfoAboutSelf(permissions.BasePermission):
    '''
    This permission class is used for the User serialization.  

    Regular users can only view information about themselves.

    Unlike other database objects where the user can "own" 
    something (likely through a foreign key relationship), here we 
    are checking that the only user information they can obtain is
    about themself
    '''

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class ReadOnly(permissions.BasePermission):
    '''
    Allows us to restrict certain ListCreate views so that 
    regular users can only list and NOT create objects.
    '''
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
