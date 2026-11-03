import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.assistant.embeddings import EmbeddingError, KnowledgeMatch, semantic_search
from apps.assistant.models import AssistantMessage
from apps.patients.models import Patient


@dataclass
class AssistantReply:
    content: str
    category: str
    safety_code: str = ""
    sources: list[dict] = field(default_factory=list)
    provider_model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")
    fallback_used: bool = False


@dataclass(frozen=True)
class ProviderReply:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")


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

FOLLOW_UP_PATTERNS = (
    "peki",
    "ya ",
    "az once",
    "onceki",
    "bunu",
    "onu",
    "bunun",
    "onun",
    "bunlar",
    "onlar",
    "devam",
    "aciklar",
    "biraz daha",
    "daha detay",
    "ne demek",
    "what about",
    "and what",
    "that ",
    "those ",
    "it ",
    "more detail",
)


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return normalized.replace("ı", "i")


def has_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in value for pattern in patterns)


def user_groups(user) -> set[str]:
    return set(user.groups.values_list("name", flat=True))


def is_doctor(user) -> bool:
    return user.is_superuser or bool(user_groups(user) & {"Admin", "Doctor"})


def authorized_patients(user):
    """Return the patient population this assistant user may query."""
    if is_doctor(user):
        return Patient.objects.filter(is_active=True)
    return Patient.objects.filter(user=user, is_active=True)


def resolve_patient(user, patient_id=None) -> Patient | None:
    """Resolve context without trusting a patient identity typed into chat."""
    if is_doctor(user):
        if not patient_id:
            return None
        return authorized_patients(user).filter(public_id=patient_id).first()
    return authorized_patients(user).first()


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
    allergies = list(patient.allergies.all())
    if patient.allergy_status == Patient.AllergyStatus.CONFIRMED and allergies:
        lines = []
        for allergy in allergies:
            details = []
            if allergy.reaction:
                details.append(
                    f"reaksiyon: {allergy.reaction}"
                    if language == "tr"
                    else f"reaction: {allergy.reaction}"
                )
            if allergy.severity != "unknown":
                severity_tr = {
                    "mild": "Hafif",
                    "moderate": "Orta",
                    "severe": "Şiddetli",
                }.get(allergy.severity, "Bilinmiyor")
                details.append(
                    f"önem: {severity_tr}"
                    if language == "tr"
                    else f"severity: {allergy.get_severity_display()}"
                )
            suffix = f" ({', '.join(details)})" if details else ""
            lines.append(f"- {allergy.allergen}{suffix}")
        heading = (
            "Carevia'da kayıtlı doğrulanmış alerjiler:"
            if language == "tr"
            else "Confirmed allergies recorded in Carevia:"
        )
        content = f"{heading}\n\n" + "\n".join(lines)
    elif patient.allergy_status == Patient.AllergyStatus.NONE_KNOWN:
        content = (
            "Carevia kaydında bilinen alerji olmadığı belirtilmiş."
            if language == "tr"
            else "The Carevia record states that there are no known allergies."
        )
    else:
        content = (
            "Carevia'da alerji durumu bilinmiyor. Bu, alerji olmadığı anlamına gelmez."
            if language == "tr"
            else "Allergy status is unknown in Carevia. This does not mean there are no allergies."
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


def is_population_allergy_query(normalized: str) -> bool:
    population_words = (
        "hastalar",
        "hasta list",
        "hasta say",
        "kac hasta",
        "kimler",
        "patients",
        "patient list",
        "which patient",
        "how many patient",
    )
    return has_any(normalized, ("alerji", "allerg")) and has_any(
        normalized, population_words
    )


def format_patients_with_allergies(user, normalized: str, language: str) -> AssistantReply:
    queryset = authorized_patients(user).filter(
        allergy_status=Patient.AllergyStatus.CONFIRMED
    )
    total = queryset.count()
    visible = list(
        queryset
        .prefetch_related("allergies")
        .order_by("last_name", "first_name")
        [:20]
    )
    count_only = has_any(normalized, ("kac", "sayisi", "toplam", "how many", "count"))
    include_details = has_any(
        normalized,
        ("alerjen", "reaksiyon", "detay", "birlikte", "allergen", "reaction", "detail"),
    )
    if count_only:
        content = (
            f"Yetkiniz kapsamındaki {total} aktif hastada doğrulanmış alerji kaydı bulunuyor."
            if language == "tr"
            else f"{total} active patients in your authorized scope have confirmed allergy records."
        )
    elif not total:
        content = (
            "Yetkiniz kapsamındaki aktif hastalarda doğrulanmış alerji kaydı bulunmuyor."
            if language == "tr"
            else "No active patients in your authorized scope have confirmed allergy records."
        )
    else:
        lines = []
        for patient in visible:
            line = f"- {patient.first_name} {patient.last_name}"
            if include_details:
                allergens = ", ".join(allergy.allergen for allergy in patient.allergies.all())
                if allergens:
                    line += f" — {allergens}"
            lines.append(line)
        heading = (
            f"Yetkiniz kapsamındaki {total} aktif hastada doğrulanmış alerji kaydı bulunuyor:"
            if language == "tr"
            else f"{total} active patients in your authorized scope have confirmed allergy records:"
        )
        content = f"{heading}\n\n" + "\n".join(lines)
        if total > len(visible):
            remaining = total - len(visible)
            content += (
                f"\n\n{remaining} sonuç daha var."
                if language == "tr"
                else f"\n\n{remaining} more results are available."
            )
    updated_at = queryset.order_by("-updated_at").values_list("updated_at", flat=True).first()
    return AssistantReply(
        content,
        "allergy_population",
        sources=[
            source(
                "Yetkili hasta kayıtları / Alerji durumu",
                "Authorized patient records / Allergy status",
                updated_at,
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
    allergy_summary = ", ".join(
        allergy.allergen for allergy in patient.allergies.all()
    ) or patient.get_allergy_status_display()
    fields = [
        f"Name: {patient.first_name} {patient.last_name}",
        f"Birth date: {patient.birth_date.isoformat()}",
        f"Allergies recorded: {allergy_summary}",
    ]
    if include_notes:
        fields.append(f"Internal clinical note: {patient.clinical_notes or 'None recorded'}")
    return "\n".join(fields)


def is_follow_up(message: str) -> bool:
    normalized = normalize(message).strip()
    return any(
        normalized == pattern.strip() or normalized.startswith(pattern)
        for pattern in FOLLOW_UP_PATTERNS
    )


def latest_user_message(history: Sequence[AssistantMessage]) -> str:
    for item in reversed(history):
        if item.role == AssistantMessage.Role.USER and item.content.strip():
            return item.content.strip()
    return ""


def contextual_query(message: str, history: Sequence[AssistantMessage]) -> str:
    previous = latest_user_message(history)
    if previous and is_follow_up(message):
        return f"{previous}\nFollow-up: {message}"
    return message


def provider_input(
    *,
    message: str,
    patient: Patient | None,
    doctor: bool,
    knowledge_matches: list[KnowledgeMatch],
    history: Sequence[AssistantMessage],
) -> list[dict[str, str]]:
    history_limit = max(0, settings.ASSISTANT_HISTORY_MESSAGES)
    char_limit = max(0, settings.ASSISTANT_HISTORY_MAX_CHARS)
    selected: list[dict[str, str]] = []
    used_chars = 0
    for item in reversed(history[-history_limit:] if history_limit else []):
        content = item.content.strip()
        if not content:
            continue
        remaining = char_limit - used_chars
        if remaining <= 0:
            break
        content = content[-remaining:]
        selected.append({"role": item.role, "content": content})
        used_chars += len(content)
    selected.reverse()

    knowledge_context = "\n\n".join(
        f"[{match.chunk.source_key}] {match.chunk.content}" for match in knowledge_matches
    ) or "No relevant approved knowledge document was found."
    current_content = (
        "Authorized Carevia patient context:\n"
        f"{patient_context_text(patient, doctor)}\n\n"
        "Approved Carevia knowledge context:\n"
        f"{knowledge_context}\n\n"
        f"Current user message:\n{message}"
    )
    return [*selected, {"role": "user", "content": current_content}]


def estimate_generation_cost(input_tokens: int, output_tokens: int) -> Decimal:
    input_cost = Decimal(str(settings.GENAI_INPUT_COST_PER_MILLION))
    output_cost = Decimal(str(settings.GENAI_OUTPUT_COST_PER_MILLION))
    return (
        Decimal(input_tokens) * input_cost + Decimal(output_tokens) * output_cost
    ) / Decimal(1_000_000)


def provider_reply(
    message: str,
    language: str,
    patient: Patient | None,
    doctor: bool,
    knowledge_matches: list[KnowledgeMatch],
    history: Sequence[AssistantMessage] = (),
) -> ProviderReply | None:
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
    payload = {
        "model": settings.GENAI_MODEL,
        "instructions": system_prompt,
        "input": provider_input(
            message=message,
            patient=patient,
            doctor=doctor,
            knowledge_matches=knowledge_matches,
            history=history,
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
    usage = body.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return ProviderReply(
        content=content,
        model=str(body.get("model") or settings.GENAI_MODEL),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_generation_cost(input_tokens, output_tokens),
    )


def create_reply(
    user,
    message: str,
    language: str,
    patient_id=None,
    history: Sequence[AssistantMessage] = (),
) -> AssistantReply:
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
    topic_words = appointment_words + allergy_words + profile_words + note_words
    routing_message = contextual_query(message, history)
    routing_normalized = (
        normalize(routing_message)
        if not has_any(normalized, topic_words) and routing_message != message
        else normalized
    )

    if has_any(routing_normalized, appointment_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_appointments(patient, language)
    if is_population_allergy_query(routing_normalized):
        if not doctor:
            return AssistantReply(
                (
                    "Toplu hasta sorguları yalnızca yetkili doktor ve yönetici hesaplarına açıktır."
                    if language == "tr"
                    else (
                        "Population-level patient queries are limited to authorized doctor "
                        "and admin accounts."
                    )
                ),
                "authorization",
                "population_query_restricted",
            )
        return format_patients_with_allergies(user, routing_normalized, language)
    if has_any(routing_normalized, allergy_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_allergies(patient, language)
    if has_any(routing_normalized, profile_words):
        if not patient:
            return missing_patient_reply(language, doctor)
        return format_profile(patient, language)
    if has_any(routing_normalized, note_words):
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
        knowledge_matches = semantic_search(contextual_query(message, history))
    except EmbeddingError:
        knowledge_matches = []

    if not knowledge_matches:
        content = (
            "Bu soruyu yanıtlamak için Carevia bilgi tabanında yeterli güvenilir bilgi "
            "bulamadım. Lütfen sorunuzu farklı şekilde ifade edin veya yetkili bir sağlık "
            "uzmanına danışın."
            if language == "tr"
            else (
                "I could not find enough reliable information in the Carevia knowledge base "
                "to answer this question. Please rephrase your question or consult a qualified "
                "healthcare professional."
            )
        )
        return AssistantReply(
            content,
            "knowledge",
            "insufficient_knowledge",
        )

    generated = provider_reply(
        message,
        language,
        patient,
        doctor,
        knowledge_matches,
        history,
    )
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
        return AssistantReply(
            generated.content,
            "generated",
            sources=sources,
            provider_model=generated.model,
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
            estimated_cost_usd=generated.estimated_cost_usd,
        )

    provider_configured = bool(
        settings.GENAI_API_URL and settings.GENAI_API_KEY and settings.GENAI_MODEL
    )

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
            fallback_used=provider_configured,
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
    return AssistantReply(content, "help", fallback_used=provider_configured)


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
