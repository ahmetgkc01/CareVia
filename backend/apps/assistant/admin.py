from django.contrib import admin

from .models import AssistantMessage, KnowledgeChunk


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "category", "safety_code", "created_at")
    list_filter = ("role", "category", "safety_code")
    search_fields = ("user__username", "content")
    readonly_fields = ("created_at",)


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "source_key",
        "chunk_index",
        "embedding_model",
        "embedding_dimensions",
        "updated_at",
    )
    search_fields = ("source_key", "content", "content_hash")
    readonly_fields = ("created_at", "updated_at")
