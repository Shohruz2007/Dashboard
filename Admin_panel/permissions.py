from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUserOrStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and (request.user.is_staff or request.user.is_superuser or request.method in SAFE_METHODS and request.user.is_analizer)
        )

class IsAdminUserOrStaffReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and ((request.user.is_staff or request.user.is_analizer) and request.method in SAFE_METHODS or request.user.is_superuser)
        )


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and (request.user.is_superuser or request.method in SAFE_METHODS and request.user.is_analizer)
        )