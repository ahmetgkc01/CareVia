import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import User


def grouped_user(username, group_name):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_admin_can_create_user_with_group():
    admin = grouped_user("user-admin", "Admin")
    Group.objects.get_or_create(name="Doctor")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/users/",
        {
            "username": "new-doctor",
            "email": "new-doctor@example.test",
            "first_name": "New",
            "last_name": "Doctor",
            "groups": ["Doctor"],
            "is_active": True,
            "password": "strong-test-password",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["groups"] == ["Doctor"]


@pytest.mark.django_db
def test_doctor_cannot_list_users():
    doctor = grouped_user("user-doctor", "Doctor")
    client = APIClient()
    client.force_authenticate(doctor)

    response = client.get("/api/users/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_auditor_can_read_but_not_change_users():
    auditor = grouped_user("user-auditor", "Auditor")
    target = grouped_user("audit-target", "Patient")
    client = APIClient()
    client.force_authenticate(auditor)

    assert client.get("/api/users/").status_code == 200
    response = client.patch(f"/api/users/{target.id}/", {"is_active": False}, format="json")
    assert response.status_code == 403

