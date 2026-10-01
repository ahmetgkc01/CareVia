import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.assistant.embeddings import EmbeddingError, KnowledgeMatch, semantic_search
from apps.patients.models import Patient


@dataclass
class AssistantReply:
    content: str
    category: str
    safety_code: str = ""
    sources: list[dict] = field(default_factory=list)


EMERGENCY_PATTERNS = (
    "nefes alam",
    "gogus agr",
    "bilincimi kay",
    "felc",
    "kendime zarar",
    "intihar",
    "asiri doz",
    "cok kanama",
    "can't breathe",
    "cannot breathe",
    "chest pain",
    "unconscious",
    "stroke",
    "self harm",
    "suicide",
    "overdose",
    "severe bleeding",
)

MEDICAL_ADVICE_PATTERNS = (
    "teshis",
    "tani koy",
    "hangi hastalik",
    "neyim var",
    "ilac oner",
    "hangi ilac",
    "doz",
    "ilacimi birak",
    "tedavimi degistir",
    "kesin sorun yok",
    "endiselenecek bir sey",
    "diagnos",
    "what disease",
    "do i have",
    "which medicine",
    "what medicine",
    "dosage",
    "stop taking",
    "change treatment",
    "nothing wrong",
    "am i okay",
)


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def has_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in value for pattern in patterns)


def user_groups(user) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


def is_doctor(user) -> bool:
    return user.is_superuser or "Doctor" in user_groups(user)


def resolve_patient(user, patient_id=None) -> Patient | None:
    """Resolve context without trusting a patient identity typed into chat."""
    if is_doctor(user):
        if not patient_id:
            return None
        return Patient.objects.filter(public_id=patient_id, is_active=True).first()
    return Patient.objects.filter(user=user, is_active=True).first()


def source(label_tr: str, label_en: str, updated_at: datetime | None, language: str) -> dict:
    return {
        "label": label_tr if language == "tr" else label_en,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def safety_reply(message: str, language: str) -> AssistantReply | None:
    normalized = normalize(message)
    if has_any(normalized, EMERGENCY_PATTERNS):
        if language == "tr":
            content = (
                "Bu mesaj acil olabilecek belirtiler içeriyor. Carevia acil durum değerlendirmesi "
                "veya teşhis yapamaz. Lütfen bulunduğunuz yerdeki acil yardım numarasını hemen "
                "arayın ya da en yakın acil servise başvurun. Mümkünse yanınızda güvendiğiniz bir "
                "kişi olsun."
            )
        else:
            content = (
                "This message may describe an emergency. Carevia cannot assess emergencies or "
                "provide a diagnosis. Please call your local emergency number now or go to the "
                "nearest emergency department. If possible, ask someone you trust to stay with you."
            )
        return AssistantReply(content, "safety", "emergency_escalation")

    if has_any(normalized, MEDICAL_ADVICE_PATTERNS):
        if language == "tr":
            content = (
                "Carevia hastalık teşhisi koyamaz; ilaç, doz veya tedavi değişikliği öneremez. "
                "Güvenilir bir değerlendirme için lütfen doktorunuzla veya yetkili bir sağlık "
                "profesyoneliyle iletişim kurun. İsterseniz Carevia'daki kayıtlı randevularınızı "
                "gösterebilirim."
            )
        else:
            content = (
                "Carevia cannot diagnose a condition or recommend medication, dosage, or treatment "
                "changes. Please contact your doctor or a qualified healthcare professional for a "
                "reliable assessment. I can show your appointments recorded in Carevia."
            )
        return AssistantReply(content, "safety", "medical_advice_blocked")
    return None


def format_appointments(patient: Patient, language: str) -> AssistantReply:
    appointments = list(
        Appointment.objects.filter(
            patient=patient,
            start_at__gte=timezone.now(),
            status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED),
        )
        .select_related("clinician__user")
        .order_by("start_at")[:5]
    )
    record_source = source(
        "Carevia randevu kayıtları",
        "Carevia appointment records",
        appointments[-1].updated_at if appointments else None,
        language,
    )
    if not appointments:
        content = (
            "Carevia kayıtlarında yaklaşan bir randevu bulunmuyor."
            if language == "tr"
            else "There are no upcoming appointments in Carevia."
        )
        return AssistantReply(content, "appointments", sources=[record_source])

    lines = []
    for appointment in appointments:
        local_start = timezone.localtime(appointment.start_at)
        clinician_name = (
            appointment.clinician.user.get_full_name()
            or appointment.clinician.user.username
        )
        lines.append(
            f"- {local_start:%d.%m.%Y %H:%M} — {clinician_name} — "
            f"{appointment.get_status_display()}"
        )
    heading = "Yaklaşan randevular:" if language == "tr" else "Upcoming appointments:"
    return AssistantReply(
        f"{heading}\n\n" + "\n".join(lines),
        "appointments",
        sources=[record_source],
    )


def format_allergies(patient: Patient, language: str) -> AssistantReply:
    allergies = patient.allergies.strip()
    if allergies:
        content = (
            f"Carevia'da kayıtlı alerji bilgisi:\n\n{allergies}"
            if language == "tr"
            else f"Allergy information recorded in Carevia:\n\n{allergies}"
        )
    else:
        content = (
            "Carevia'da kayıtlı bir alerji bilgisi bulunmuyor. "
            "Bu, alerjiniz olmadığı anlamına gelmez."
            if language == "tr"
            else (
                "No allergy information is recorded in Carevia. "
                "This does not mean you have no allergies."
            )
        )
    return AssistantReply(
        content,
        "allergies",
        sources=[
            source(
                "Hasta kaydı / Alerjiler",
                "Patient record / Allergies",
                patient.updated_at,
                language,
            )
        ],
    )


def format_profile(patient: Patient, language: str) -> AssistantReply:
    if language == "tr":
        content = (
            f"Carevia hasta profili:\n\n"
            f"- Ad soyad: {patient.first_name} {patient.last_name}\n"
            f"- Doğum tarihi: {patient.birth_date:%d.%m.%Y}\n"
            f"- Tercih edilen dil: {patient.get_preferred_language_display()}\n"
            f"- Ülke kodu: {patient.country_code or 'Belirtilmemiş'}"
        )
    else:
        content = (
            f"Carevia patient profile:\n\n"
            f"- Full name: {patient.first_name} {patient.last_name}\n"
            f"- Birth date: {patient.birth_date:%Y-%m-%d}\n"
            f"- Preferred language: {patient.get_preferred_language_display()}\n"
            f"- Country code: {patient.country_code or 'Not specified'}"
        )
    return AssistantReply(
        content,
        "profile",
        sources=[source("Hasta profili", "Patient profile", patient.updated_at, language)],
    )


def format_clinical_notes(patient: Patient, language: str) -> AssistantReply:
    notes = patient.clinical_notes.strip()
    content = notes or (
        "Klinik not bulunmuyor." if language == "tr" else "No clinical note is recorded."
    )
    prefix = "Dahili klinik not:\n\n" if language == "tr" else "Internal clinical note:\n\n"
    return AssistantReply(
        prefix + content,
        "clinical_notes",
        sources=[
            source(
                "Dahili klinik not",
                "Internal clinical note",
                patient.updated_at,
                language,
            )
        ],
    )


def patient_context_text(patient: Patient | None, include_notes: bool) -> str:
    if not patient:
        return "No patient context is selected."
    fields = [
        f"Name: {patient.first_name} {patient.last_name}",
        f"Birth date: {patient.birth_date.isoformat()}",
        f"Allergies recorded: {patient.allergies or 'None recorded'}",
    ]
    if include_notes:
        fields.append(f"Internal clinical note: {patient.clinical_notes or 'None recorded'}")
    return "\n".join(fields)


def provider_reply(
    message: str,
    language: str,
    patient: Patient | None,
    doctor: bool,
    knowledge_matches: list[KnowledgeMatch],
) -> str | None:
    if not (settings.GENAI_API_URL and settings.GENAI_API_KEY and settings.GENAI_MODEL):
        return None
    system_prompt = (
        "You are Carevia's healthcare administration assistant. Use only the supplied Carevia "
        "context. Never diagnose, recommend a drug or dosage, change treatment, promise that a "
        "condition is harmless, or make an emergency decision. Never claim access to data outside "
        "the context. Ask the user to contact a qualified healthcare professional for medical "
        "judgment. Keep the answer concise and use "
        + ("Turkish." if language == "tr" else "English.")
    )
    knowledge_context = "\n\n".join(
        f"[{match.chunk.source_key}] {match.chunk.content}" for match in knowledge_matches
    ) or "No relevant approved knowledge document was found."
    payload = {
        "model": settings.GENAI_MODEL,
        "instructions": system_prompt,
        "input": (
            "Authorized Carevia patient context:\n"
            f"{patient_context_text(patient, doctor)}\n\n"
            "Approved Carevia knowledge context:\n"
            f"{knowledge_context}\n\n"
            f"User message:\n{message}"
        ),
        "max_output_tokens": 350,
        "store": False,
    }
    request = Request(
        settings.GENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.GENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.GENAI_TIMEOUT_SECONDS) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        content = next(
            part["text"].strip()
            for item in body["output"]
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text" and part.get("text", "").strip()
        )
    except (
        HTTPError,
        URLError,
        TimeoutError,
        KeyError,
        IndexError,
        StopIteration,
        TypeError,
        ValueError,
    ):
        return None

    normalized = normalize(content)
    unsafe_output_patterns = (
        "ilacinizi birak",
        "tani niz",
        "you have been diagnosed",
        "stop taking",
    )
    if has_any(normalized, unsafe_output_patterns) or re.search(r"\b\d+\s*(mg|ml)\b", normalized):
        return None
    return content


def create_reply(user, message: str, language: str, patient_id=None) -> AssistantReply:
    blocked = safety_reply(message, language)
    if blocked:
        return blocked

    doctor = is_doctor(user)
    patient = resolve_patient(user, patient_id)
    normalized = normalize(message)

    appointment_words = ("randevu", "appointment", "takvim", "schedule")
    allergy_words = ("alerji", "allerg")
    profile_words = ("profil", "bilgilerim", "my information", "profile")
    note_words = ("klinik not", "doktor not", "clinical note", "doctor note")

    if has_any(normalized, appointment_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_appointments(patient, language)
    if has_any(normalized, allergy_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_allergies(patient, language)
    if has_any(normalized, profile_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_profile(patient, language)
    if has_any(normalized, note_words):
        if not doctor:
            content = (
                "Dahili klinik notlar hasta hesabına gösterilmez. Sağlık durumunuzla ilgili "
                "bilgi için lütfen doktorunuzla iletişim kurun."
                if language == "tr"
                else (
                    "Internal clinical notes are not shown to patient accounts. Please contact "
                    "your doctor for information about your health."
                )
            )
            return AssistantReply(content, "authorization", "clinical_notes_restricted")
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_clinical_notes(patient, language)

    try:
        knowledge_matches = semantic_search(message)
    except EmbeddingError:
        knowledge_matches = []

    generated = provider_reply(message, language, patient, doctor, knowledge_matches)
    if generated:
        sources = knowledge_sources(knowledge_matches)
        if patient:
            sources.append(
                source(
                    "Yetkili hasta kaydı",
                    "Authorized patient record",
                    patient.updated_at,
                    language,
                )
            )
        return AssistantReply(generated, "generated", sources=sources)

    if knowledge_matches:
        heading = (
            "Carevia bilgi tabanında şu bilgiler bulunuyor:"
            if language == "tr"
            else "The Carevia knowledge base contains the following information:"
        )
        excerpts = "\n\n".join(match.chunk.content for match in knowledge_matches)
        return AssistantReply(
            f"{heading}\n\n{excerpts}",
            "knowledge",
            sources=knowledge_sources(knowledge_matches),
        )

    if language == "tr":
        content = (
            "Randevular, kayıtlı alerjiler ve hasta profili hakkında yardımcı olabilirim. "
            "Doktor hesabındaysanız önce bir hasta seçebilirsiniz. Tıbbi teşhis, ilaç, doz veya "
            "tedavi önerisi veremem."
        )
    else:
        content = (
            "I can help with appointments, recorded allergies, and the patient profile. If you are "
            "using a doctor account, select a patient first. I cannot provide a diagnosis or "
            "recommend medication, dosage, or treatment changes."
        )
    return AssistantReply(content, "help")


def knowledge_sources(matches: list[KnowledgeMatch]) -> list[dict]:
    results = []
    for match in matches:
        results.append(
            {
                "label": match.chunk.metadata.get("label") or match.chunk.source_key,
                "updated_at": match.chunk.updated_at.isoformat(),
                "source_key": match.chunk.source_key,
                "distance": round(match.distance, 4),
            }
        )
    return results


def missing_patient_reply(language: str, doctor: bool) -> AssistantReply:
    if doctor:
        content = (
            "Bu bilgi için önce sohbet ekranından bir hasta seçin."
            if language == "tr"
            else "Select a patient in the chat screen first."
        )
    else:
        content = (
            "Hesabınıza bağlı aktif bir hasta profili bulunamadı. "
            "Lütfen Carevia yöneticisiyle iletişim kurun."
            if language == "tr"
            else (
                "No active patient profile is linked to your account. "
                "Please contact a Carevia administrator."
            )
        )
    return AssistantReply(content, "missing_context", "patient_context_required")
