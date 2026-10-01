import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clinicians", "0001_initial"),
        ("patients", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("no_show", "No-show")], default="scheduled", max_length=20)),
                ("reason", models.CharField(blank=True, max_length=250)),
                ("internal_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("clinician", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="clinicians.clinician")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_appointments", to=settings.AUTH_USER_MODEL)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="patients.patient")),
            ],
            options={
                "ordering": ("start_at",),
                "indexes": [
                    models.Index(fields=["clinician", "start_at", "end_at"], name="appointment_clinici_9babfa_idx"),
                    models.Index(fields=["patient", "start_at"], name="appointment_patient_4b5ed5_idx"),
                    models.Index(fields=["status", "start_at"], name="appointment_status_013fbb_idx"),
                ],
            },
        )
    ]

