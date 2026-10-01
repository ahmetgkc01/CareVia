import hashlib
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from pgvector.django import CosineDistance

from .models import KnowledgeChunk


class EmbeddingError(RuntimeError):
    """Raised when an embedding cannot be created safely."""


@dataclass(frozen=True)
class KnowledgeMatch:
    chunk: KnowledgeChunk
    distance: float


def generate_embedding(text: str) -> list[float]:
    cleaned_text = text.strip()
    if not cleaned_text:
        raise EmbeddingError("Embedding text cannot be empty.")
    if not settings.EMBEDDING_API_KEY:
        raise EmbeddingError("EMBEDDING_API_KEY is not configured.")

    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": cleaned_text,
        "dimensions": settings.EMBEDDING_DIMENSIONS,
        "encoding_format": "float",
    }
    request = Request(
        settings.EMBEDDING_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.EMBEDDING_TIMEOUT_SECONDS) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        embedding = body["data"][0]["embedding"]
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise EmbeddingError("The embedding provider request failed.") from exc

    if not isinstance(embedding, list) or len(embedding) != settings.EMBEDDING_DIMENSIONS:
        raise EmbeddingError("The embedding provider returned an unexpected vector size.")
    return embedding


def upsert_knowledge_chunk(
    *,
    source_key: str,
    chunk_index: int,
    content: str,
    metadata: dict | None = None,
) -> tuple[KnowledgeChunk, bool]:
    cleaned_content = content.strip()
    if not source_key.strip() or not cleaned_content:
        raise EmbeddingError("A source key and non-empty content are required.")

    content_hash = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()
    existing = KnowledgeChunk.objects.filter(
        source_key=source_key,
        chunk_index=chunk_index,
    ).first()
    if (
        existing
        and existing.content_hash == content_hash
        and existing.embedding_model == settings.EMBEDDING_MODEL
        and existing.embedding_dimensions == settings.EMBEDDING_DIMENSIONS
        and existing.embedding is not None
    ):
        return existing, False

    vector = generate_embedding(cleaned_content)
    chunk, _ = KnowledgeChunk.objects.update_or_create(
        source_key=source_key,
        chunk_index=chunk_index,
        defaults={
            "content": cleaned_content,
            "content_hash": content_hash,
            "metadata": metadata or {},
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
            "embedding": vector,
        },
    )
    return chunk, True


def semantic_search(query: str, limit: int | None = None) -> list[KnowledgeMatch]:
    vector = generate_embedding(query)
    result_limit = limit or settings.KNOWLEDGE_SEARCH_LIMIT
    queryset = (
        KnowledgeChunk.objects.filter(
            embedding__isnull=False,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        )
        .annotate(distance=CosineDistance("embedding", vector))
        .filter(distance__lte=settings.KNOWLEDGE_MAX_COSINE_DISTANCE)
        .order_by("distance", "id")[:result_limit]
    )
    return [KnowledgeMatch(chunk=item, distance=float(item.distance)) for item in queryset]
