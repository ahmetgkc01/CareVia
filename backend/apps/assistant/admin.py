from django.contrib import admin

from .models import AssistantMessage, KnowledgeChunk


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "patient",
        "role",
        "category",
        "provider_model",
        "latency_ms",
        "fallback_used",
        "created_at",
    )
    list_filter = ("role", "category", "safety_code", "fallback_used", "provider_model")
    search_fields = ("user__username", "content")
    readonly_fields = (
        "provider_model",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "latency_ms",
        "fallback_used",
        "created_at",
    )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "source_key",
        "chunk_index",
        "content_preview",
        "embedding_model",
        "embedding_dimensions",
        "has_embedding",
        "updated_at",
    )
    search_fields = ("source_key", "content", "content_hash")
    exclude = ("embedding",)
    readonly_fields = ("embedding_preview", "created_at", "updated_at")

    @admin.display(description="İçerik")
    def content_preview(self, chunk):
        return f"{chunk.content[:90]}{'…' if len(chunk.content) > 90 else ''}"

    @admin.display(boolean=True, description="Vektör var")
    def has_embedding(self, chunk):
        return chunk.embedding is not None

    @admin.display(description="Vektör önizleme")
    def embedding_preview(self, chunk):
        if chunk.embedding is None:
            return "—"
        values = list(chunk.embedding)
        preview = ", ".join(f"{value:.6f}" for value in values[:12])
        return f"[{preview}, …] ({len(values)} boyut)"
