from rest_framework.permissions import SAFE_METHODS, BasePermission

READ_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary", "Patient", "Auditor"}


class ClinicianPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if request.method in SAFE_METHODS:
            return bool(groups & READ_GROUPS)
        return "Admin" in groups

