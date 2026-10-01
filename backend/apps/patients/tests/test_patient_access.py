from datetime import date

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.patients.models import Patient


@pytest.fixture
def api_client():
    return APIClient()


def create_user(username, group_name):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_doctor_can_list_all_patients(api_client):
    doctor = create_user("doctor", "Doctor")
    Patient.objects.create(first_name="Ada", last_name="Example", birth_date=date(1990, 1, 1))
    Patient.objects.create(first_name="Mert", last_name="Example", birth_date=date(1985, 1, 1))
    api_client.force_authenticate(doctor)

    response = api_client.get("/api/patients/")

    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_patient_can_only_list_own_record(api_client):
    first_user = create_user("patient-one", "Patient")
    second_user = create_user("patient-two", "Patient")
    own_patient = Patient.objects.create(
        user=first_user,
        first_name="Ada",
        last_name="Example",
        birth_date=date(1990, 1, 1),
    )
    Patient.objects.create(
        user=second_user,
        first_name="Mert",
        last_name="Example",
        birth_date=date(1985, 1, 1),
    )
    api_client.force_authenticate(first_user)

    response = api_client.get("/api/patients/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["public_id"] == str(own_patient.public_id)
    assert "clinical_notes" not in response.data["results"][0]


@pytest.mark.django_db
def test_secretary_cannot_read_clinical_fields(api_client):
    secretary = create_user("secretary", "Secretary")
    Patient.objects.create(
        first_name="Ada",
        last_name="Example",
        birth_date=date(1990, 1, 1),
        allergies="Synthetic allergy",
        clinical_notes="Internal clinical note",
    )
    api_client.force_authenticate(secretary)

    response = api_client.get("/api/patients/")

    assert response.status_code == 200
    assert "allergies" not in response.data["results"][0]
    assert "clinical_notes" not in response.data["results"][0]

