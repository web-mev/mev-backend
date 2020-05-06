from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    '''
    The purpose of this permission class is to limit 
    viewing or editing of resources to the owner OR to
    someone with administrative privileges.

    Assumes the instance `obj` has an `owner` attribute
    '''

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.owner == request.user


class IsInfoAboutSelf(permissions.BasePermission):
    '''
    This permission class is used for the User serialization.  

    Admins can view anyone's details.

    Regular users can only view information about themselves.

    Unlike other database objects where the user can "own" 
    something (likely through a foreign key relationship), here we 
    are checking that the only user information they can obtain is
    about themself
    '''

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj == request.user
