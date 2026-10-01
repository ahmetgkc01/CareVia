from .middleware import client_ip
from .models import AuditEvent


def record_event(request, *, action, status_code, user=None, username=""):
    resolved_user = user if user is not None and user.is_authenticated else None
    AuditEvent.objects.create(
        user=resolved_user,
        username=(resolved_user.get_username() if resolved_user else username)[:150],
        action=action,
        method=request.method,
        path=request.path[:500],
        status_code=status_code,
        ip_address=client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
