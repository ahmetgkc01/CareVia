from rest_framework.permissions import BasePermission


class IsAssistantUser(BasePermission):
    """Limit assistant access to clinical/admin staff and patients."""

    message = "The assistant is available to admin, doctor, and patient accounts only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        return bool(groups & {"Admin", "Doctor", "Patient"})
