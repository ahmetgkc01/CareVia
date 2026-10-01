from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "clinician", "start_at", "end_at", "status")
    list_filter = ("status", "clinician")
    search_fields = ("patient__first_name", "patient__last_name", "reason")

