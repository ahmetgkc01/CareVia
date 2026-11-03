from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Allergy, Patient


class Command(BaseCommand):
    help = "Create isolated synthetic accounts used by browser end-to-end tests."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_e2e is disabled when DEBUG is false.")

        admin_group, _ = Group.objects.get_or_create(name="Admin")
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")
        patient_group, _ = Group.objects.get_or_create(name="Patient")
        admin = self.ensure_user("e2e_admin", "e2e_admin@carevia.local", options["password"])
        doctor = self.ensure_user(
            "e2e_doctor",
            "e2e_doctor@carevia.local",
            options["password"],
        )
        patient = self.ensure_user(
            "e2e_patient",
            "e2e_patient@carevia.local",
            options["password"],
        )
        admin.groups.set([admin_group])
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=("is_staff", "is_superuser"))
        doctor.groups.set([doctor_group])
        patient.groups.set([patient_group])
        patient_record, _ = Patient.objects.update_or_create(
            user=patient,
            defaults={
                "first_name": "E2E",
                "last_name": "Patient",
                "birth_date": "1990-01-01",
                "preferred_language": "tr",
                "allergy_status": Patient.AllergyStatus.CONFIRMED,
            },
        )
        Allergy.objects.update_or_create(
            patient=patient_record,
            allergen="Synthetic E2E pollen",
            defaults={
                "reaction": "Synthetic E2E sneezing",
                "severity": Allergy.Severity.MILD,
            },
        )
        clinician, _ = Clinician.objects.update_or_create(
            user=doctor,
            defaults={
                "profession": Clinician.Profession.DOCTOR,
                "specialty": "Aile Hekimliği",
                "is_active": True,
            },
        )
        start_at = timezone.now() + timedelta(days=1)
        Appointment.objects.update_or_create(
            patient=patient_record,
            clinician=clinician,
            reason="Synthetic E2E follow-up",
            defaults={
                "start_at": start_at,
                "end_at": start_at + timedelta(minutes=30),
                "status": Appointment.Status.CONFIRMED,
                "created_by": admin,
            },
        )
        self.stdout.write(self.style.SUCCESS("Synthetic E2E accounts are ready."))

    @staticmethod
    def ensure_user(username, email, password):
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.first_name = "E2E"
        user.last_name = username.removeprefix("e2e_").title()
        user.is_active = True
        user.set_password(password)
        user.save()
        return user
