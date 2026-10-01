import uuid

from django.conf import settings
from django.db import models


class Clinician(models.Model):
    class Profession(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        NURSE = "nurse", "Nurse"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinician_profile",
    )
    profession = models.CharField(max_length=20, choices=Profession.choices)
    specialty = models.CharField(max_length=120, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

