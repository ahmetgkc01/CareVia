import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient


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
