from rest_framework import permissions

class EtudiantPermission(permissions.BasePermission):
     def has_permission(self, request, view):
        if request.user.is_authenticated:
            if request.user.userprofile.role == "direction" or request.user.userprofile.role == "enseignant" :
                return True
            elif request.method in permissions.SAFE_METHODS:
                return True
        return False


class ClassePermission(permissions.BasePermission):
    pass


# Antso
class IsDirectionUser(permissions.BasePermission):
    """
    Permission pour s'assurer que seul le rôle 'direction' peut accéder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == "direction"

class IsFinanceUser(permissions.BasePermission):
    """
    Permission pour s'assurer que seul le rôle 'finance' peut accéder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == "finance"

class IsEnseignantUser(permissions.BasePermission):
    """
    Permission pour s'assurer que seul le rôle 'enseignant' peut accéder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == "enseignant"

class IsParentUser(permissions.BasePermission):
    """
    Permission pour s'assurer que seul le rôle 'parent' peut accéder.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == "parent"

class IsDirectionOrFinanceUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = getattr(request.user.userprofile, 'role', None)
        return role in ['direction', 'finance']
