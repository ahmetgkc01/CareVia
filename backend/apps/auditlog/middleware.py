from ipaddress import ip_address

from .models import AuditEvent

EXCLUDED_PATHS = {
    "/api/health/",
    "/api/schema/",
    "/api/docs/",
    "/api/session/csrf/",
    "/api/session/login/",
    "/api/session/logout/",
}


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    value = forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    if not value:
        return None
    try:
        return str(ip_address(value))
    except ValueError:
        return None


def action_for(request):
    return "read" if request.method in {"GET", "HEAD", "OPTIONS"} else "write"


class AuditLogMiddleware:
    """Record authenticated API access without storing request or response bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if (
            request.path.startswith("/api/")
            and request.path not in EXCLUDED_PATHS
            and user is not None
            and user.is_authenticated
        ):
            AuditEvent.objects.create(
                user=user,
                username=user.get_username(),
                action=action_for(request),
                method=request.method,
                path=request.path[:500],
                status_code=response.status_code,
                ip_address=client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        return response
