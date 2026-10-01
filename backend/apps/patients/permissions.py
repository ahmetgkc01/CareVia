from rest_framework.permissions import SAFE_METHODS, BasePermission

STAFF_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary", "Auditor"}


class PatientAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if groups & STAFF_GROUPS:
            if "Auditor" in groups:
                return request.method in SAFE_METHODS
            return True
        return "Patient" in groups and request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if groups & STAFF_GROUPS:
            return request.method in SAFE_METHODS or "Auditor" not in groups
        return (
            "Patient" in groups
            and obj.user_id == request.user.id
            and request.method in SAFE_METHODS
        )

