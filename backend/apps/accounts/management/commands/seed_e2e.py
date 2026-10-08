from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.patients.models import Patient


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
        doctor.groups.set([doctor_group])
        patient.groups.set([patient_group])
        Patient.objects.update_or_create(
            user=patient,
            defaults={
                "first_name": "E2E",
                "last_name": "Patient",
                "birth_date": "1990-01-01",
                "preferred_language": "tr",
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
