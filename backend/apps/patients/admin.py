from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "birth_date", "country_code", "is_active")
    list_filter = ("is_active", "gender", "country_code", "preferred_language")
    search_fields = ("first_name", "last_name", "email", "phone")
    readonly_fields = ("public_id", "created_at", "updated_at")

