from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient


def user_with_group(username, group_name):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


@pytest.fixture
def dashboard_records():
    doctor_user = user_with_group("dashboard-doctor", "Doctor")
    clinician = Clinician.objects.create(user=doctor_user, profession="doctor", is_active=True)
    first_user = user_with_group("dashboard-patient-one", "Patient")
    second_user = user_with_group("dashboard-patient-two", "Patient")
    first_patient = Patient.objects.create(
        user=first_user,
        first_name="Ada",
        last_name="Example",
        birth_date="1990-01-01",
    )
    second_patient = Patient.objects.create(
        user=second_user,
        first_name="Mert",
        last_name="Example",
        birth_date="1985-01-01",
    )
    start_at = timezone.now() + timedelta(days=1)
    for patient in (first_patient, second_patient):
        Appointment.objects.create(
            patient=patient,
            clinician=clinician,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            status="confirmed",
        )
    return doctor_user, first_user


@pytest.mark.django_db
def test_staff_dashboard_counts_all_records(dashboard_records):
    doctor_user, _ = dashboard_records
    client = APIClient()
    client.force_authenticate(doctor_user)

    response = client.get("/api/dashboard/summary/")

    assert response.status_code == 200
    assert response.data == {
        "scope": "staff",
        "total_patients": 2,
        "upcoming_appointments": 2,
        "active_clinicians": 1,
        "active_doctors": 1,
        "active_nurses": 0,
        "care_team": [],
    }


@pytest.mark.django_db
def test_patient_dashboard_only_counts_own_records(dashboard_records):
    _, patient_user = dashboard_records
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.get("/api/dashboard/summary/")

    assert response.status_code == 200
    assert response.data["scope"] == "patient"
    assert response.data["total_patients"] == 1
    assert response.data["upcoming_appointments"] == 1
    assert response.data["active_clinicians"] == 0
    assert response.data["active_doctors"] == 0
    assert response.data["active_nurses"] == 0
    assert response.data["care_team"] == [
        {
            "public_id": str(Clinician.objects.get().public_id),
            "display_name": "",
            "profession": "doctor",
            "specialty": "",
        }
    ]


@pytest.mark.django_db
def test_user_without_carevia_role_cannot_read_dashboard():
    user = User.objects.create_user(
        username="unassigned-user",
        email="unassigned@example.test",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/dashboard/summary/")

    assert response.status_code == 403

