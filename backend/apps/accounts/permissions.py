from rest_framework.permissions import SAFE_METHODS, BasePermission


class UserManagementPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if "Admin" in groups:
            return True
        return "Auditor" in groups and request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if obj.is_superuser:
            return False
        return not obj.groups.filter(name="Admin").exists()

