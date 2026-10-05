from rest_framework.throttling import SimpleRateThrottle


class AssistantRateThrottle(SimpleRateThrottle):
    """Limit costly assistant message creation per authenticated user."""

    scope = "assistant"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
