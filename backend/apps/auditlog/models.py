from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=40)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("user", "created_at"), name="audit_user_created_idx"),
            models.Index(fields=("action", "created_at"), name="audit_action_created_idx"),
        ]

    def __str__(self):
        return f"{self.created_at.isoformat()} {self.username} {self.action}"
