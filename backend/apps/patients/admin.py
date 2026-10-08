from django.contrib import admin

from .models import Allergy, Patient


class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "birth_date",
        "allergy_status",
        "country_code",
        "is_active",
    )
    list_filter = (
        "is_active",
        "allergy_status",
        "gender",
        "country_code",
        "preferred_language",
    )
    search_fields = ("first_name", "last_name", "email", "phone")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (AllergyInline,)

