import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
def test_health_check_verifies_database(client, monkeypatch):
    monkeypatch.setenv("CAREVIA_RELEASE", "test-release")
    response = client.get(reverse("health-check"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "release": "test-release"}


@pytest.mark.django_db
def test_release_overview_returns_recent_commits(client, monkeypatch):
    group = Group.objects.create(name="Admin")
    user = User.objects.create_user(
        username="release-admin",
        email="release-admin@example.test",
        password="test-password",
    )
    user.groups.add(group)
    client.force_login(user)
    monkeypatch.setenv("CAREVIA_RELEASE", "abc1234")
    monkeypatch.setattr(
        "apps.dashboard.views.recent_commits",
        lambda: [
            {
                "sha": "abc123456789",
                "committed_at": "2026-10-09T18:23:15+03:00",
                "message": "feat: show release history",
            }
        ],
    )

    response = client.get(reverse("release-overview"))

    assert response.status_code == 200
    assert response.json()["release"] == "abc1234"
    assert response.json()["commits"][0]["message"] == "feat: show release history"


@pytest.mark.django_db
def test_patient_cannot_read_release_overview(client):
    group = Group.objects.create(name="Patient")
    user = User.objects.create_user(
        username="release-patient",
        email="release-patient@example.test",
        password="test-password",
    )
    user.groups.add(group)
    client.force_login(user)

    response = client.get(reverse("release-overview"))

    assert response.status_code == 403


def test_bundled_commits_uses_deployed_release(monkeypatch, tmp_path, settings):
    from apps.dashboard.views import bundled_commits

    history = tmp_path / "release_history.json"
    history.write_text(
        '{"current":{"committed_at":"2026-10-09T21:00:00+03:00",'
        '"message":"feat: release"},"previous":[]}',
        encoding="utf-8",
    )
    settings.BASE_DIR = tmp_path
    monkeypatch.setenv("CAREVIA_RELEASE", "deployed-sha")

    assert bundled_commits() == [
        {
            "sha": "deployed-sha",
            "committed_at": "2026-10-09T21:00:00+03:00",
            "message": "feat: release",
        }
    ]
