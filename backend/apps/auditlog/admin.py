from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "username",
        "action",
        "method",
        "path",
        "status_code",
        "ip_address",
    )
    list_filter = ("action", "method", "status_code", "created_at")
    search_fields = ("username", "path", "ip_address")
    readonly_fields = (
        "user",
        "username",
        "action",
        "method",
        "path",
        "status_code",
        "ip_address",
        "user_agent",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
