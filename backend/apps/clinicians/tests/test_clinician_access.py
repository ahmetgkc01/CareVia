import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clinicians.models import Clinician


def user_with_group(username, group_name=None):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
    )
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_patient_cannot_read_clinician_directory():
    doctor = user_with_group("listed-doctor", "Doctor")
    Clinician.objects.create(user=doctor, profession="doctor")
    client = APIClient()
    client.force_authenticate(user_with_group("patient-reader", "Patient"))

    response = client.get("/api/clinicians/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_user_without_carevia_role_cannot_read_clinicians():
    client = APIClient()
    client.force_authenticate(user_with_group("unassigned-reader"))

    assert client.get("/api/clinicians/").status_code == 403


@pytest.mark.django_db
def test_admin_can_create_clinician_and_assign_role():
    client = APIClient()
    client.force_authenticate(user_with_group("clinician-admin", "Admin"))

    response = client.post(
        "/api/clinicians/",
        {
            "username": "new-doctor",
            "first_name": "Ada",
            "last_name": "Example",
            "email": "new-doctor@example.test",
            "password": "test-password",
            "profession": "doctor",
            "specialty": "Cardiology",
            "country_code": "TR",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert User.objects.get(username="new-doctor").groups.filter(name="Doctor").exists()


@pytest.mark.django_db
def test_doctor_cannot_create_clinician():
    client = APIClient()
    client.force_authenticate(user_with_group("clinician-doctor", "Doctor"))

    response = client.post(
        "/api/clinicians/",
        {
            "username": "forbidden-doctor",
            "first_name": "Test",
            "last_name": "Doctor",
            "email": "forbidden@example.test",
            "password": "test-password",
            "profession": "doctor",
        },
        format="json",
    )

    assert response.status_code == 403
    assert not User.objects.filter(username="forbidden-doctor").exists()
