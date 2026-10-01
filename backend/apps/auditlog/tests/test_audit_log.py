import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.auditlog.models import AuditEvent


@pytest.mark.django_db
def test_authenticated_api_access_is_logged_without_payload():
    user = User.objects.create_user(
        username="audit-doctor",
        email="audit-doctor@example.test",
        password="test-password",
    )
    group, _ = Group.objects.get_or_create(name="Doctor")
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/dashboard/summary/")

    assert response.status_code == 200
    event = AuditEvent.objects.get(user=user, path="/api/dashboard/summary/")
    assert event.action == "read"
    assert event.method == "GET"
    assert event.status_code == 200
