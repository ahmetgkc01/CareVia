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


@pytest.mark.django_db
def test_admin_cannot_assign_admin_role():
    admin = grouped_user("regular-admin", "Admin")
    Group.objects.get_or_create(name="Patient")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/users/",
        {
            "username": "forbidden-admin",
            "email": "forbidden-admin@example.test",
            "first_name": "Forbidden",
            "last_name": "Admin",
            "groups": ["Admin"],
            "is_active": True,
            "password": "strong-test-password",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(username="forbidden-admin").exists()


@pytest.mark.django_db
def test_admin_cannot_change_another_admin():
    acting_admin = grouped_user("acting-admin", "Admin")
    protected_admin = grouped_user("protected-admin", "Admin")
    patient_group, _ = Group.objects.get_or_create(name="Patient")
    client = APIClient()
    client.force_authenticate(acting_admin)

    response = client.patch(
        f"/api/users/{protected_admin.id}/",
        {"groups": [patient_group.name], "is_active": False},
        format="json",
    )

    assert response.status_code == 403
    protected_admin.refresh_from_db()
    assert protected_admin.is_active
    assert protected_admin.groups.filter(name="Admin").exists()


@pytest.mark.django_db
def test_super_user_can_assign_and_revoke_admin_role():
    super_user = User.objects.create_superuser(
        username="super-user",
        email="super-user@example.test",
        password="test-password",
    )
    Group.objects.get_or_create(name="Admin")
    target = grouped_user("admin-target", "Patient")
    client = APIClient()
    client.force_authenticate(super_user)

    promote_response = client.patch(
        f"/api/users/{target.id}/",
        {"groups": ["Admin"]},
        format="json",
    )
    assert promote_response.status_code == 200

    demote_response = client.patch(
        f"/api/users/{target.id}/",
        {"groups": ["Patient"]},
        format="json",
    )
    assert demote_response.status_code == 200
    assert demote_response.data["groups"] == ["Patient"]


@pytest.mark.django_db
def test_super_user_account_is_not_exposed_by_user_management_api():
    super_user = User.objects.create_superuser(
        username="protected-super-user",
        email="protected-super-user@example.test",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(super_user)

    assert client.get(f"/api/users/{super_user.id}/").status_code == 404
    assert client.patch(
        f"/api/users/{super_user.id}/",
        {"is_active": False},
        format="json",
    ).status_code == 404

    super_user.refresh_from_db()
    assert super_user.is_active
    assert super_user.is_superuser

