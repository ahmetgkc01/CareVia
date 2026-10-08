import uuid

from django.conf import settings
from django.db import models


class Patient(models.Model):
    class AllergyStatus(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed allergies"
        NONE_KNOWN = "none_known", "No known allergies"
        UNKNOWN = "unknown", "Unknown"

    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "non_binary", "Non-binary"
        OTHER = "other", "Other"
        UNDISCLOSED = "undisclosed", "Prefer not to say"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="patient_profile",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2")
    preferred_language = models.CharField(
        max_length=10,
        choices=(("tr", "Türkçe"), ("en", "English")),
        default="tr",
    )
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=40, blank=True)
    allergy_status = models.CharField(
        max_length=20,
        choices=AllergyStatus.choices,
        default=AllergyStatus.UNKNOWN,
    )
    clinical_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [
            models.Index(fields=("last_name", "first_name")),
            models.Index(fields=("is_active",)),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Allergy(models.Model):
    class Severity(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        MILD = "mild", "Mild"
        MODERATE = "moderate", "Moderate"
        SEVERE = "severe", "Severe"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="allergies",
    )
    allergen = models.TextField()
    reaction = models.CharField(max_length=500, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.UNKNOWN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("allergen", "id")

    def __str__(self):
        return f"{self.patient}: {self.allergen}"

