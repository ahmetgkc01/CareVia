from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient


def create_user(username, group_name):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


@pytest.fixture
def appointment_data():
    doctor_user = create_user("doctor-appointment", "Doctor")
    clinician = Clinician.objects.create(
        user=doctor_user,
        profession=Clinician.Profession.DOCTOR,
        specialty="Family medicine",
    )
    first_user = create_user("patient-appointment-one", "Patient")
    second_user = create_user("patient-appointment-two", "Patient")
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
    first_appointment = Appointment.objects.create(
        patient=first_patient,
        clinician=clinician,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=30),
        reason="Synthetic check-up",
        internal_notes="Staff-only note",
        created_by=doctor_user,
    )
    Appointment.objects.create(
        patient=second_patient,
        clinician=clinician,
        start_at=start_at + timedelta(hours=1),
        end_at=start_at + timedelta(hours=1, minutes=30),
        created_by=doctor_user,
    )
    return doctor_user, first_user, clinician, first_patient, first_appointment


@pytest.mark.django_db
def test_patient_only_sees_own_appointments_without_internal_notes(appointment_data):
    _, patient_user, _, _, own_appointment = appointment_data
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.get("/api/appointments/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["public_id"] == str(own_appointment.public_id)
    assert "internal_notes" not in response.data["results"][0]


@pytest.mark.django_db
def test_overlapping_clinician_appointment_is_rejected(appointment_data):
    doctor_user, _, clinician, patient, appointment = appointment_data
    client = APIClient()
    client.force_authenticate(doctor_user)

    response = client.post(
        "/api/appointments/",
        {
            "patient_id": str(patient.public_id),
            "clinician_id": str(clinician.public_id),
            "start_at": (appointment.start_at + timedelta(minutes=10)).isoformat(),
            "end_at": (appointment.end_at + timedelta(minutes=10)).isoformat(),
            "status": "scheduled",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_doctor_can_list_all_appointments(appointment_data):
    doctor_user, _, _, _, _ = appointment_data
    client = APIClient()
    client.force_authenticate(doctor_user)

    response = client.get("/api/appointments/")

    assert response.status_code == 200
    assert response.data["count"] == 2

