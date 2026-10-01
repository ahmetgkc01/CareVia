import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
def test_user_can_login_read_session_and_logout():
    User.objects.create_user(
        username="doctor",
        email="doctor@example.test",
        password="test-password",
    )
    client = APIClient(enforce_csrf_checks=True)

    csrf_response = client.get("/api/session/csrf/")
    csrf_token = csrf_response.cookies["csrftoken"].value
    login_response = client.post(
        "/api/session/login/",
        {"username": "doctor", "password": "test-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        HTTP_ORIGIN="http://127.0.0.1:5173",
    )

    assert login_response.status_code == 200
    assert login_response.data["username"] == "doctor"
    assert client.get("/api/session/me/").status_code == 200

    rotated_csrf_token = client.cookies["csrftoken"].value
    logout_response = client.post(
        "/api/session/logout/",
        HTTP_X_CSRFTOKEN=rotated_csrf_token,
    )
    assert logout_response.status_code == 204
    assert client.get("/api/session/me/").status_code == 403


@pytest.mark.django_db
def test_login_rejects_request_without_csrf_token():
    User.objects.create_user(
        username="doctor",
        email="doctor@example.test",
        password="test-password",
    )
    client = APIClient(enforce_csrf_checks=True)

    response = client.post(
        "/api/session/login/",
        {"username": "doctor", "password": "test-password"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_login_attempts_are_rate_limited():
    cache.clear()
    User.objects.create_user(
        username="rate-limited-user",
        email="rate-limited@example.test",
        password="correct-password",
    )
    client = APIClient(enforce_csrf_checks=True)
    csrf_response = client.get("/api/session/csrf/")
    csrf_token = csrf_response.cookies["csrftoken"].value

    for _ in range(5):
        response = client.post(
            "/api/session/login/",
            {"username": "rate-limited-user", "password": "wrong-password"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        assert response.status_code == 400

    response = client.post(
        "/api/session/login/",
        {"username": "rate-limited-user", "password": "wrong-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 429

