from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.assistant.embeddings import EmbeddingError, upsert_knowledge_chunk
from apps.assistant.models import KnowledgeChunk


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []

    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start + (chunk_size // 2):
                end = boundary
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = end - overlap
    return chunks


class Command(BaseCommand):
    help = "Embed an approved text file and store its chunks in the pgvector knowledge base."

    def add_arguments(self, parser):
        parser.add_argument("--source-key", required=True)
        parser.add_argument("--file", required=True)
        parser.add_argument("--label", default="")
        parser.add_argument("--language", choices=("tr", "en"), default="tr")
        parser.add_argument("--chunk-size", type=int, default=1200)
        parser.add_argument("--overlap", type=int, default=200)
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.is_file():
            raise CommandError(f"File not found: {file_path}")
        if options["chunk_size"] < 200:
            raise CommandError("--chunk-size must be at least 200.")
        if not 0 <= options["overlap"] < options["chunk_size"]:
            raise CommandError("--overlap must be non-negative and smaller than --chunk-size.")

        chunks = split_text(
            file_path.read_text(encoding="utf-8"),
            options["chunk_size"],
            options["overlap"],
        )
        if not chunks:
            raise CommandError("The file does not contain any text.")

        source_key = options["source_key"].strip()
        if options["replace"]:
            KnowledgeChunk.objects.filter(source_key=source_key).delete()

        changed = 0
        try:
            for index, content in enumerate(chunks):
                _, was_changed = upsert_knowledge_chunk(
                    source_key=source_key,
                    chunk_index=index,
                    content=content,
                    metadata={
                        "label": options["label"] or source_key,
                        "language": options["language"],
                        "filename": file_path.name,
                    },
                )
                changed += int(was_changed)
        except EmbeddingError as exc:
            raise CommandError(str(exc)) from exc

        KnowledgeChunk.objects.filter(source_key=source_key, chunk_index__gte=len(chunks)).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Stored {len(chunks)} chunk(s) for {source_key}; {changed} embedding(s) created."
            )
        )
