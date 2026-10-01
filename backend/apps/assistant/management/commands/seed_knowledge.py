from django.core.management.base import BaseCommand, CommandError

from apps.assistant.embeddings import EmbeddingError, upsert_knowledge_chunk

APPROVED_DEMO_KNOWLEDGE = (
    (
        "carevia-assistant-scope",
        "Carevia Asistan kapsamı",
        "Carevia Asistan randevuları, hasta profilindeki kayıtlı bilgileri ve kayıtlı alerjileri "
        "gösterebilir. Asistan teşhis koymaz; ilaç, doz veya tedavi değişikliği önermez. Acil bir "
        "durumda yerel acil yardım numarası aranmalı veya en yakın acil servise başvurulmalıdır.",
    ),
    (
        "carevia-privacy",
        "Carevia gizlilik yaklaşımı",
        "Carevia geliştirme ve test ortamında yalnızca sentetik veya anonimleştirilmiş veri "
        "kullanır. "
        "Hasta hesabı yalnızca kendisine bağlı kaydı görebilir. Doktor hesabı, sohbet ekranında "
        "yetkili olduğu hastayı seçerek ilgili kayıtlara erişebilir.",
    ),
    (
        "carevia-appointments",
        "Carevia randevu işlemleri",
        "Carevia randevu ekranında yaklaşan randevular tarih, saat, sağlık profesyoneli ve durum "
        "bilgileriyle gösterilir. Randevu kaydı bulunmaması, sağlık hizmetine ihtiyaç olmadığı "
        "anlamına gelmez.",
    ),
    (
        "carevia-data-quality",
        "Carevia veri doğruluğu",
        "Carevia yalnızca sistemde kayıtlı bilgiyi gösterir. Eksik bir kayıt, ilgili bilginin "
        "gerçekte olmadığını kanıtlamaz. Hatalı veya eksik bilgiler yetkili Carevia yöneticisine "
        "bildirilmelidir.",
    ),
)


class Command(BaseCommand):
    help = "Create a small synthetic Carevia knowledge base and generate its embeddings."

    def handle(self, *args, **options):
        changed = 0
        try:
            for source_key, label, content in APPROVED_DEMO_KNOWLEDGE:
                _, was_changed = upsert_knowledge_chunk(
                    source_key=source_key,
                    chunk_index=0,
                    content=content,
                    metadata={"label": label, "language": "tr", "synthetic": True},
                )
                changed += int(was_changed)
        except EmbeddingError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(APPROVED_DEMO_KNOWLEDGE)} approved chunk(s); "
                f"{changed} embedding(s) created."
            )
        )
