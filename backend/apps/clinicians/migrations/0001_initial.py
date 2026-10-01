import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Clinician",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("profession", models.CharField(choices=[("doctor", "Doctor"), ("nurse", "Nurse")], max_length=20)),
                ("specialty", models.CharField(blank=True, max_length=120)),
                ("country_code", models.CharField(blank=True, max_length=2)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="clinician_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("user__last_name", "user__first_name")},
        )
    ]

