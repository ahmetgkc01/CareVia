from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class AssistantMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_messages",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        related_name="assistant_messages",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    category = models.CharField(max_length=40, blank=True)
    safety_code = models.CharField(max_length=40, blank=True)
    sources = models.JSONField(default=list, blank=True)
    provider_model = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0,
    )
    latency_ms = models.PositiveIntegerField(default=0)
    fallback_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=("user", "created_at")),
            models.Index(
                fields=("user", "patient", "created_at"),
                name="assistant_history_context_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.role}:{self.created_at.isoformat()}"


class KnowledgeChunk(models.Model):
    """A synthetic or approved text fragment used for semantic retrieval."""

    source_key = models.CharField(max_length=200)
    chunk_index = models.PositiveIntegerField(default=0)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    embedding_model = models.CharField(max_length=100, default="text-embedding-3-small")
    embedding_dimensions = models.PositiveSmallIntegerField(default=1536)
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("source_key", "chunk_index")
        constraints = [
            models.UniqueConstraint(
                fields=("source_key", "chunk_index"),
                name="unique_knowledge_source_chunk",
            )
        ]
        indexes = [
            models.Index(fields=("content_hash",)),
            HnswIndex(
                name="knowledge_embedding_hnsw",
                fields=("embedding",),
                m=16,
                ef_construction=64,
                opclasses=("vector_cosine_ops",),
            ),
        ]

    def __str__(self):
        return f"{self.source_key}:{self.chunk_index}"
