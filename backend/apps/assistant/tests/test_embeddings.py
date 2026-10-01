import json
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.assistant.embeddings import EmbeddingError, generate_embedding, upsert_knowledge_chunk
from apps.assistant.management.commands.ingest_knowledge import split_text
from apps.assistant.models import KnowledgeChunk


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


@override_settings(
    EMBEDDING_API_KEY="test-key",
    EMBEDDING_MODEL="text-embedding-3-small",
    EMBEDDING_DIMENSIONS=3,
)
def test_generate_embedding_uses_configured_dimensions():
    with patch(
        "apps.assistant.embeddings.urlopen",
        return_value=FakeResponse({"data": [{"embedding": [0.1, 0.2, 0.3]}]}),
    ) as mocked_urlopen:
        result = generate_embedding("approved synthetic text")

    assert result == [0.1, 0.2, 0.3]
    request_body = json.loads(mocked_urlopen.call_args.args[0].data)
    assert request_body["model"] == "text-embedding-3-small"
    assert request_body["dimensions"] == 3


@override_settings(EMBEDDING_API_KEY="")
def test_generate_embedding_requires_api_key():
    with pytest.raises(EmbeddingError, match="EMBEDDING_API_KEY"):
        generate_embedding("text")


@pytest.mark.django_db
@override_settings(EMBEDDING_MODEL="text-embedding-3-small", EMBEDDING_DIMENSIONS=1536)
def test_upsert_skips_unchanged_embedding():
    vector = [0.0] * 1536
    with patch("apps.assistant.embeddings.generate_embedding", return_value=vector) as generate:
        first, first_changed = upsert_knowledge_chunk(
            source_key="demo-policy",
            chunk_index=0,
            content="Synthetic approved policy",
            metadata={"label": "Demo"},
        )
        second, second_changed = upsert_knowledge_chunk(
            source_key="demo-policy",
            chunk_index=0,
            content="Synthetic approved policy",
            metadata={"label": "Demo"},
        )

    assert first.pk == second.pk
    assert first_changed is True
    assert second_changed is False
    assert generate.call_count == 1
    assert KnowledgeChunk.objects.count() == 1


def test_split_text_uses_overlap_and_keeps_all_text():
    text = " ".join(f"word-{index}" for index in range(80))
    chunks = split_text(text, chunk_size=200, overlap=30)

    assert len(chunks) > 1
    assert chunks[0][-30:].strip() in chunks[1]
