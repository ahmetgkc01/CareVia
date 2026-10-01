import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Patient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("birth_date", models.DateField()),
                ("gender", models.CharField(blank=True, choices=[("female", "Female"), ("male", "Male"), ("non_binary", "Non-binary"), ("other", "Other"), ("undisclosed", "Prefer not to say")], max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("address", models.TextField(blank=True)),
                ("country_code", models.CharField(blank=True, help_text="ISO 3166-1 alpha-2", max_length=2)),
                ("preferred_language", models.CharField(choices=[("tr", "Türkçe"), ("en", "English")], default="tr", max_length=10)),
                ("emergency_contact_name", models.CharField(blank=True, max_length=200)),
                ("emergency_contact_phone", models.CharField(blank=True, max_length=40)),
                ("allergies", models.TextField(blank=True)),
                ("clinical_notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="patient_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("last_name", "first_name"),
                "indexes": [models.Index(fields=["last_name", "first_name"], name="patients_pa_last_na_1b32a7_idx"), models.Index(fields=["is_active"], name="patients_pa_is_acti_54ba9f_idx")],
            },
        )
    ]

