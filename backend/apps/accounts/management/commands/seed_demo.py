from datetime import date, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient

FIRST_NAMES = (
    "Ayşe", "Mehmet", "Elif", "Deniz", "Zeynep", "Mert", "Selin", "Can", "Derya", "Emre",
    "Emma", "Liam", "Sofia", "Noah", "Mia", "Lucas", "Olivia", "Daniel", "Amelia", "Leo",
)

LAST_NAMES = (
    "Demir",
    "Kaya",
    "Yılmaz",
    "Aydın",
    "Şahin",
    "Çelik",
    "Arslan",
    "Koç",
    "Öztürk",
    "Aksoy",
    "Wilson",
    "Anderson",
    "Martin",
    "Müller",
    "Rossi",
    "Silva",
    "Taylor",
    "Brown",
    "Garcia",
    "Novak",
)

SPECIALTIES = (
    "Family Medicine", "Internal Medicine", "Cardiology", "Dermatology", "Neurology",
    "Pediatrics", "Psychiatry", "Orthopedics",
)

COUNTRIES = ("TR", "TR", "TR", "TR", "GB", "US", "DE", "FR", "IT", "BR")


def generated_name(index: int, offset: int = 0) -> tuple[str, str]:
    first_name = FIRST_NAMES[(index + offset) % len(FIRST_NAMES)]
    last_name = LAST_NAMES[((index + offset) * 7) % len(LAST_NAMES)]
    return first_name, last_name


class Command(BaseCommand):
    help = "Create a deterministic, configurable synthetic Carevia dataset."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True)
        parser.add_argument("--patients", type=int, default=250)
        parser.add_argument("--doctors", type=int, default=20)
        parser.add_argument("--nurses", type=int, default=20)
        parser.add_argument("--secretaries", type=int, default=5)
        parser.add_argument("--auditors", type=int, default=3)
        parser.add_argument("--appointments", type=int, default=600)
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords for demo users that already exist.",
        )

    def handle(self, *args, **options):
        count_names = (
            "patients", "doctors", "nurses", "secretaries", "auditors", "appointments",
        )
        if any(options[name] < 0 for name in count_names):
            raise CommandError("Seed counts cannot be negative.")
        if options["appointments"] and (not options["patients"] or not options["doctors"]):
            raise CommandError("Appointments require at least one patient and one doctor.")

        password = options["password"]
        reset_passwords = options["reset_passwords"]
        groups = {
            name: Group.objects.get_or_create(name=name)[0]
            for name in ("Admin", "Doctor", "Nurse", "Secretary", "Patient", "Auditor")
        }

        admin = self.ensure_user(
            username="admin",
            email="admin@carevia.local",
            first_name="Carevia",
            last_name="Admin",
            password=password,
            group=groups["Admin"],
            is_staff=True,
            is_superuser=True,
            reset_passwords=reset_passwords,
        )

        doctors = self.create_clinicians(
            count=options["doctors"],
            profession=Clinician.Profession.DOCTOR,
            group=groups["Doctor"],
            password=password,
            reset_passwords=reset_passwords,
        )
        nurses = self.create_clinicians(
            count=options["nurses"],
            profession=Clinician.Profession.NURSE,
            group=groups["Nurse"],
            password=password,
            reset_passwords=reset_passwords,
        )
        patients = self.create_patients(
            options["patients"],
            groups["Patient"],
            password,
            reset_passwords,
        )

        self.create_staff_users(
            role="secretary",
            count=options["secretaries"],
            group=groups["Secretary"],
            password=password,
            name_offset=9,
            reset_passwords=reset_passwords,
        )
        self.create_staff_users(
            role="auditor",
            count=options["auditors"],
            group=groups["Auditor"],
            password=password,
            name_offset=14,
            reset_passwords=reset_passwords,
        )
        self.create_appointments(
            count=options["appointments"],
            patients=patients,
            doctors=doctors,
            created_by=admin,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Synthetic Carevia demo data is ready: "
                f"{len(patients)} patients, {len(doctors)} doctors, {len(nurses)} nurses, "
                f"{options['secretaries']} secretaries, {options['auditors']} auditors, "
                f"{options['appointments']} appointments."
            )
        )

    @staticmethod
    def ensure_user(
        *,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        group: Group,
        is_staff: bool = False,
        is_superuser: bool = False,
        reset_passwords: bool = False,
    ) -> User:
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        if created or reset_passwords or not user.has_usable_password():
            user.set_password(password)
        user.save()
        user.groups.add(group)
        return user

    def create_clinicians(
        self,
        *,
        count: int,
        profession: str,
        group: Group,
        password: str,
        reset_passwords: bool,
    ) -> list[Clinician]:
        clinicians = []
        role = "doctor" if profession == Clinician.Profession.DOCTOR else "nurse"
        for index in range(count):
            first_name, last_name = generated_name(index, 3 if role == "doctor" else 11)
            username = role if index == 0 else f"{role}{index + 1:03d}"
            user = self.ensure_user(
                username=username,
                email=f"{username}@carevia.local",
                first_name=first_name,
                last_name=last_name,
                password=password,
                group=group,
                reset_passwords=reset_passwords,
            )
            clinician, _ = Clinician.objects.update_or_create(
                user=user,
                defaults={
                    "profession": profession,
                    "specialty": SPECIALTIES[index % len(SPECIALTIES)] if role == "doctor" else "",
                    "country_code": "TR",
                    "is_active": True,
                },
            )
            clinicians.append(clinician)
        return clinicians

    def create_patients(
        self,
        count: int,
        group: Group,
        password: str,
        reset_passwords: bool,
    ) -> list[Patient]:
        patients = []
        genders = tuple(value for value, _ in Patient.Gender.choices)
        for index in range(count):
            first_name, last_name = generated_name(index)
            username = "patient" if index == 0 else f"patient{index + 1:03d}"
            user = self.ensure_user(
                username=username,
                email=f"{username}@carevia.local",
                first_name=first_name,
                last_name=last_name,
                password=password,
                group=group,
                reset_passwords=reset_passwords,
            )
            country_code = COUNTRIES[index % len(COUNTRIES)]
            patient, _ = Patient.objects.update_or_create(
                # Preserve the original seed key so existing demo databases expand safely.
                email=f"synthetic.patient{index + 1}@example.test",
                defaults={
                    "user": user,
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": date(
                        1945 + ((index * 7) % 60),
                        (index % 12) + 1,
                        (index % 27) + 1,
                    ),
                    "gender": genders[index % len(genders)],
                    "country_code": country_code,
                    "preferred_language": "tr" if country_code == "TR" else "en",
                    "phone": f"+999000{index + 1:06d}",
                    "address": "Synthetic demo address",
                    "emergency_contact_name": "Synthetic Contact",
                    "emergency_contact_phone": f"+999100{index + 1:06d}",
                    "allergies": (
                        "Synthetic pollen allergy" if index % 4 == 0 else "No known allergies"
                    ),
                    "clinical_notes": "Synthetic demonstration record. Not a real patient.",
                    "is_active": index % 25 != 24,
                },
            )
            patients.append(patient)
        return patients

    def create_staff_users(
        self,
        *,
        role: str,
        count: int,
        group: Group,
        password: str,
        name_offset: int,
        reset_passwords: bool,
    ) -> None:
        for index in range(count):
            first_name, last_name = generated_name(index, name_offset)
            username = role if index == 0 else f"{role}{index + 1:03d}"
            self.ensure_user(
                username=username,
                email=f"{username}@carevia.local",
                first_name=first_name,
                last_name=last_name,
                password=password,
                group=group,
                reset_passwords=reset_passwords,
            )

    @staticmethod
    def create_appointments(
        *,
        count: int,
        patients: list[Patient],
        doctors: list[Clinician],
        created_by: User,
    ) -> None:
        if not count:
            return
        base_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        for index in range(count):
            day_offset = (index % 181) - 60
            start_at = base_time + timedelta(days=day_offset, hours=index % 9)
            status = (
                Appointment.Status.COMPLETED
                if day_offset < 0
                else (
                    Appointment.Status.CONFIRMED
                    if index % 2
                    else Appointment.Status.SCHEDULED
                )
            )
            Appointment.objects.update_or_create(
                reason=f"Synthetic demo appointment #{index + 1:04d}",
                defaults={
                    "patient": patients[index % len(patients)],
                    "clinician": doctors[index % len(doctors)],
                    "start_at": start_at,
                    "end_at": start_at + timedelta(minutes=30),
                    "status": status,
                    "internal_notes": "Synthetic staff-only note.",
                    "created_by": created_by,
                },
            )
