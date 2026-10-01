from rest_framework.permissions import SAFE_METHODS, BasePermission

STAFF_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary", "Auditor"}
WRITE_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary"}


class AppointmentPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if request.method in SAFE_METHODS:
            return bool(groups & STAFF_GROUPS or "Patient" in groups)
        return bool(groups & WRITE_GROUPS)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        if "Patient" in groups:
            return request.method in SAFE_METHODS and obj.patient.user_id == request.user.id
        if "Auditor" in groups:
            return request.method in SAFE_METHODS
        return bool(groups & WRITE_GROUPS)

