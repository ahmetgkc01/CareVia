from django.contrib import admin

from .models import Clinician


@admin.register(Clinician)
class ClinicianAdmin(admin.ModelAdmin):
    list_display = ("user", "profession", "specialty", "country_code", "is_active")
    list_filter = ("profession", "specialty", "country_code", "is_active")
    search_fields = ("user__first_name", "user__last_name", "user__email")

