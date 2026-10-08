import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.assistant.embeddings import KnowledgeMatch
from apps.assistant.models import AssistantMessage, KnowledgeChunk
from apps.assistant.services import create_reply, provider_reply
from apps.assistant.throttles import AssistantRateThrottle
from apps.clinicians.models import Clinician
from apps.patients.models import Allergy, Patient


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
def assistant_records():
    doctor_user = user_with_group("assistant-doctor", "Doctor")
    clinician = Clinician.objects.create(user=doctor_user, profession="doctor")
    patient_user = user_with_group("assistant-patient", "Patient")
    other_user = user_with_group("assistant-other-patient", "Patient")
    patient = Patient.objects.create(
        user=patient_user,
        first_name="Ada",
        last_name="Example",
        birth_date="1990-01-01",
        allergy_status=Patient.AllergyStatus.CONFIRMED,
        clinical_notes="Internal synthetic note",
    )
    other_patient = Patient.objects.create(
        user=other_user,
        first_name="Other",
        last_name="Example",
        birth_date="1985-01-01",
        allergy_status=Patient.AllergyStatus.CONFIRMED,
    )
    Allergy.objects.create(patient=patient, allergen="Synthetic pollen allergy")
    Allergy.objects.create(patient=other_patient, allergen="Private synthetic latex allergy")
    start_at = timezone.now() + timedelta(days=1)
    Appointment.objects.create(
        patient=patient,
        clinician=clinician,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=30),
        status=Appointment.Status.CONFIRMED,
    )
    return doctor_user, patient_user, patient, other_patient


@pytest.mark.django_db
def test_patient_can_read_only_own_allergy_context(assistant_records):
    _, patient_user, _, other_patient = assistant_records
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.post(
        "/api/assistant/messages/",
        {
            "message": "Alerjilerim neler?",
            "language": "tr",
            "patient_id": str(other_patient.public_id),
        },
        format="json",
    )

    assert response.status_code == 201
    assert "Synthetic pollen allergy" in response.data["content"]
    assert "latex" not in response.data["content"]


@pytest.mark.django_db
def test_doctor_can_use_explicit_patient_context(assistant_records):
    doctor_user, _, _, other_patient = assistant_records
    client = APIClient()
    client.force_authenticate(doctor_user)

    response = client.post(
        "/api/assistant/messages/",
        {
            "message": "Hastanın alerjileri neler?",
            "language": "tr",
            "patient_id": str(other_patient.public_id),
        },
        format="json",
    )

    assert response.status_code == 201
    assert "Private synthetic latex allergy" in response.data["content"]


@pytest.mark.django_db
def test_doctor_can_list_patients_with_confirmed_allergies_without_context(assistant_records):
    doctor_user, _, _, _ = assistant_records
    Patient.objects.create(
        first_name="No",
        last_name="Allergy",
        birth_date="1992-01-01",
        allergy_status=Patient.AllergyStatus.NONE_KNOWN,
    )
    client = APIClient()
    client.force_authenticate(doctor_user)

    response = client.post(
        "/api/assistant/messages/",
        {"message": "Alerjisi olan hastaları listele", "language": "tr"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["category"] == "allergy_population"
    assert "Ada Example" in response.data["content"]
    assert "Other Example" in response.data["content"]
    assert "No Allergy" not in response.data["content"]
    assert response.data["safety_code"] == ""


@pytest.mark.django_db
def test_admin_group_can_use_assistant_population_query(assistant_records):
    admin = user_with_group("assistant-admin", "Admin")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/assistant/messages/",
        {"message": "Kaç hastada alerji kaydı var?", "language": "tr"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["category"] == "allergy_population"
    assert "2 aktif hastada" in response.data["content"]


@pytest.mark.django_db
def test_patient_cannot_run_population_query(assistant_records):
    _, patient_user, _, _ = assistant_records
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.post(
        "/api/assistant/messages/",
        {"message": "Alerjisi olan hastalar kimler?", "language": "tr"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["safety_code"] == "population_query_restricted"
    assert "Other Example" not in response.data["content"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("prompt", "safety_code"),
    [
        ("Bana teşhis koyar mısın?", "medical_advice_blocked"),
        ("Göğüs ağrım var ve nefes alamıyorum", "emergency_escalation"),
    ],
)
def test_medical_and_emergency_requests_are_blocked(assistant_records, prompt, safety_code):
    _, patient_user, _, _ = assistant_records
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.post(
        "/api/assistant/messages/",
        {"message": prompt, "language": "tr"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["category"] == "safety"
    assert response.data["safety_code"] == safety_code


@pytest.mark.django_db
def test_patient_cannot_read_internal_clinical_notes(assistant_records):
    _, patient_user, _, _ = assistant_records
    client = APIClient()
    client.force_authenticate(patient_user)

    response = client.post(
        "/api/assistant/messages/",
        {"message": "Doktor notumu göster", "language": "tr"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["safety_code"] == "clinical_notes_restricted"
    assert "Internal synthetic note" not in response.data["content"]


@pytest.mark.django_db
def test_history_is_scoped_and_can_be_cleared(assistant_records):
    _, patient_user, _, _ = assistant_records
    other_user = user_with_group("history-other", "Patient")
    AssistantMessage.objects.create(user=other_user, role="user", content="private")
    client = APIClient()
    client.force_authenticate(patient_user)
    client.post(
        "/api/assistant/messages/",
        {"message": "Randevularım", "language": "tr"},
        format="json",
    )

    history = client.get("/api/assistant/messages/")
    assert history.status_code == 200
    assert len(history.data) == 2
    assert all(message["content"] != "private" for message in history.data)

    assert client.delete("/api/assistant/messages/").status_code == 204
    assert not AssistantMessage.objects.filter(user=patient_user).exists()
    assert AssistantMessage.objects.filter(user=other_user).exists()


@pytest.mark.django_db
def test_non_doctor_staff_cannot_use_first_release(assistant_records):
    nurse = user_with_group("assistant-nurse", "Nurse")
    client = APIClient()
    client.force_authenticate(nurse)

    response = client.get("/api/assistant/messages/")

    assert response.status_code == 403


@pytest.mark.django_db
@patch.dict(AssistantRateThrottle.THROTTLE_RATES, {"assistant": "1/hour"})
def test_assistant_message_creation_is_rate_limited(assistant_records):
    _, patient_user, _, _ = assistant_records
    cache.clear()
    client = APIClient()
    client.force_authenticate(patient_user)
    payload = {"message": "RandevularÄ±m", "language": "tr"}

    assert client.post("/api/assistant/messages/", payload, format="json").status_code == 201
    assert client.post("/api/assistant/messages/", payload, format="json").status_code == 429
    assert client.get("/api/assistant/messages/").status_code == 200
    cache.clear()


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Safe response"}],
                    }
                ]
            }
        ).encode("utf-8")


@override_settings(
    GENAI_API_URL="https://api.openai.com/v1/responses",
    GENAI_API_KEY="test-key",
    GENAI_MODEL="test-model",
)
def test_provider_uses_responses_api_shape():
    with patch("apps.assistant.services.urlopen", return_value=FakeResponse()) as mocked_urlopen:
        result = provider_reply("What can Carevia do?", "en", None, False, [])

    assert result == "Safe response"
    payload = json.loads(mocked_urlopen.call_args.args[0].data)
    assert payload["store"] is False
    assert payload["input"].endswith("User message:\nWhat can Carevia do?")
    assert "messages" not in payload


@pytest.mark.django_db
def test_knowledge_fallback_returns_sources():
    user = user_with_group("knowledge-patient", "Patient")
    chunk = KnowledgeChunk.objects.create(
        source_key="carevia-scope",
        chunk_index=0,
        content="Carevia shows approved synthetic records.",
        content_hash="a" * 64,
        metadata={"label": "Carevia scope"},
    )
    matches = [KnowledgeMatch(chunk=chunk, distance=0.12)]

    with (
        patch("apps.assistant.services.semantic_search", return_value=matches),
        patch("apps.assistant.services.provider_reply", return_value=None),
    ):
        reply = create_reply(user, "Carevia ne yapar?", "tr")

    assert reply.category == "knowledge"
    assert "approved synthetic records" in reply.content
    assert reply.sources[0]["source_key"] == "carevia-scope"
    assert reply.sources[0]["distance"] == 0.12
