import django.db.models.deletion
from django.db import migrations, models


NO_KNOWN_ALLERGY_VALUES = {
    "no known allergies",
    "no known allergy",
    "bilinen alerji yok",
    "alerji yok",
    "yok",
    "none",
}


def migrate_allergies(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    Allergy = apps.get_model("patients", "Allergy")

    for patient in Patient.objects.all().iterator():
        legacy_value = (patient.allergies or "").strip()
        normalized = legacy_value.casefold()
        if not legacy_value:
            patient.allergy_status = "unknown"
        elif normalized in NO_KNOWN_ALLERGY_VALUES:
            patient.allergy_status = "none_known"
        else:
            patient.allergy_status = "confirmed"
            Allergy.objects.create(
                patient=patient,
                allergen=legacy_value,
                severity="unknown",
            )
        patient.save(update_fields=("allergy_status",))


def restore_legacy_allergies(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    Allergy = apps.get_model("patients", "Allergy")

    for patient in Patient.objects.all().iterator():
        if patient.allergy_status == "confirmed":
            legacy_value = "; ".join(
                Allergy.objects.filter(patient=patient)
                .order_by("allergen", "id")
                .values_list("allergen", flat=True)
            )
        elif patient.allergy_status == "none_known":
            legacy_value = "No known allergies"
        else:
            legacy_value = ""
        patient.allergies = legacy_value
        patient.save(update_fields=("allergies",))


class Migration(migrations.Migration):
    dependencies = [("patients", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="allergy_status",
            field=models.CharField(
                choices=[
                    ("confirmed", "Confirmed allergies"),
                    ("none_known", "No known allergies"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Allergy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("allergen", models.TextField()),
                ("reaction", models.CharField(blank=True, max_length=500)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("unknown", "Unknown"),
                            ("mild", "Mild"),
                            ("moderate", "Moderate"),
                            ("severe", "Severe"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="structured_allergies",
                        to="patients.patient",
                    ),
                ),
            ],
            options={"ordering": ("allergen", "id")},
        ),
        migrations.RunPython(migrate_allergies, restore_legacy_allergies),
        migrations.RemoveField(model_name="patient", name="allergies"),
        migrations.AlterField(
            model_name="allergy",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="allergies",
                to="patients.patient",
            ),
        ),
    ]
