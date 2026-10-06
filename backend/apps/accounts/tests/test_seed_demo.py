import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.accounts.management.commands.seed_demo import ROLE_NAME_OFFSETS, generated_name
from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient


def test_default_demo_name_ranges_are_unique_across_roles():
    role_counts = {
        "patient": 250,
        "doctor": 20,
        "nurse": 20,
        "secretary": 5,
        "auditor": 3,
    }
    names = [
        generated_name(index, ROLE_NAME_OFFSETS[role])
        for role, count in role_counts.items()
        for index in range(count)
    ]

    assert len(names) == 298
    assert len(set(names)) == len(names)


@pytest.mark.django_db
def test_seed_demo_creates_configurable_synthetic_dataset():
    call_command(
        "seed_demo",
        password="test-password",
        patients=6,
        doctors=2,
        nurses=3,
        secretaries=2,
        auditors=1,
        appointments=8,
    )

    assert Patient.objects.count() == 6
    assert Clinician.objects.filter(profession=Clinician.Profession.DOCTOR).count() == 2
    assert Clinician.objects.filter(profession=Clinician.Profession.NURSE).count() == 3
    assert Appointment.objects.count() == 8
    assert User.objects.count() == 15
    assert set(Group.objects.values_list("name", flat=True)) == {
        "Admin",
        "Doctor",
        "Nurse",
        "Secretary",
        "Patient",
        "Auditor",
    }


@pytest.mark.django_db
def test_seed_demo_is_idempotent_for_the_same_counts():
    options = {
        "password": "test-password",
        "patients": 3,
        "doctors": 1,
        "nurses": 1,
        "secretaries": 1,
        "auditors": 1,
        "appointments": 4,
    }
    call_command("seed_demo", **options)
    call_command("seed_demo", **options)

    assert Patient.objects.count() == 3
    assert Clinician.objects.count() == 2
    assert Appointment.objects.count() == 4


@pytest.mark.django_db
def test_refresh_demo_names_updates_users_and_linked_patients_without_other_changes():
    call_command(
        "seed_demo",
        password="test-password",
        patients=6,
        doctors=2,
        nurses=2,
        secretaries=1,
        auditors=1,
        appointments=3,
    )
    User.objects.exclude(username="admin").update(first_name="Can", last_name="Aksoy")
    Patient.objects.update(first_name="Can", last_name="Aksoy")
    appointment_ids = list(Appointment.objects.values_list("id", flat=True))

    call_command("refresh_demo_names")

    demo_users = User.objects.exclude(username="admin")
    names = list(demo_users.values_list("first_name", "last_name"))
    assert len(names) == len(set(names))
    assert list(Appointment.objects.values_list("id", flat=True)) == appointment_ids
    assert not Patient.objects.filter(first_name="Can", last_name="Aksoy").exists()
    assert all(
        patient.first_name == patient.user.first_name
        and patient.last_name == patient.user.last_name
        for patient in Patient.objects.select_related("user")
    )
