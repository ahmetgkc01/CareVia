from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.management.commands.seed_demo import ROLE_NAME_OFFSETS, generated_name
from apps.accounts.models import User
from apps.patients.models import Patient


@dataclass(frozen=True)
class DemoNameUpdate:
    user: User
    role: str
    index: int
    first_name: str
    last_name: str


ROLE_GROUPS = {
    "patient": "Patient",
    "doctor": "Doctor",
    "nurse": "Nurse",
    "secretary": "Secretary",
    "auditor": "Auditor",
}


def demo_user_index(username: str, role: str) -> int | None:
    if username == role:
        return 0
    if not username.startswith(role):
        return None
    suffix = username.removeprefix(role)
    if not suffix.isdigit():
        return None
    ordinal = int(suffix)
    return ordinal - 1 if ordinal >= 2 else None


class Command(BaseCommand):
    help = "Refresh deterministic names for existing synthetic Carevia demo accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report the updates without changing the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        updates: list[DemoNameUpdate] = []
        for role, group_name in ROLE_GROUPS.items():
            users = (
                User.objects.filter(
                    email__endswith="@carevia.local",
                    groups__name=group_name,
                )
                .distinct()
                .order_by("username")
            )
            for user in users:
                index = demo_user_index(user.username, role)
                if index is None or user.email != f"{user.username}@carevia.local":
                    continue
                first_name, last_name = generated_name(index, ROLE_NAME_OFFSETS[role])
                updates.append(
                    DemoNameUpdate(user, role, index, first_name, last_name)
                )

        desired_names = [(update.first_name, update.last_name) for update in updates]
        if len(desired_names) != len(set(desired_names)):
            raise CommandError(
                "Generated demo names are not unique for the existing account counts."
            )

        changed_users = 0
        changed_patients = 0
        for update in updates:
            if (
                update.user.first_name != update.first_name
                or update.user.last_name != update.last_name
            ):
                changed_users += 1
                if not options["dry_run"]:
                    User.objects.filter(pk=update.user.pk).update(
                        first_name=update.first_name,
                        last_name=update.last_name,
                    )

            if update.role == "patient":
                patient = Patient.objects.filter(
                    user=update.user,
                    email=f"synthetic.patient{update.index + 1}@example.test",
                ).first()
                if patient and (
                    patient.first_name != update.first_name
                    or patient.last_name != update.last_name
                ):
                    changed_patients += 1
                    if not options["dry_run"]:
                        Patient.objects.filter(pk=patient.pk).update(
                            first_name=update.first_name,
                            last_name=update.last_name,
                        )

        mode = "Dry run" if options["dry_run"] else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {changed_users} demo users and "
                f"{changed_patients} linked patient records."
            )
        )
