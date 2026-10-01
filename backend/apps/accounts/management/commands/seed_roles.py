from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMISSIONS = {
    "Admin": ["add_patient", "change_patient", "delete_patient", "view_patient"],
    "Doctor": ["add_patient", "change_patient", "view_patient"],
    "Nurse": ["add_patient", "change_patient", "view_patient"],
    "Secretary": ["add_patient", "change_patient", "view_patient"],
    "Patient": ["view_patient"],
    "Auditor": ["view_patient"],
}


class Command(BaseCommand):
    help = "Create the initial Carevia roles and patient permissions."

    def handle(self, *args, **options):
        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            permissions = Permission.objects.filter(
                content_type__app_label="patients",
                codename__in=codenames,
            )
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"Role synchronized: {role}"))

