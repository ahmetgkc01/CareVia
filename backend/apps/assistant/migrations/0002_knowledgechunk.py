import pgvector.django.vector
from django.db import migrations, models


def enable_vector_extension(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")


class Migration(migrations.Migration):
    dependencies = [("assistant", "0001_initial")]

    operations = [
        migrations.RunPython(enable_vector_extension, migrations.RunPython.noop),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_key", models.CharField(max_length=200)),
                ("chunk_index", models.PositiveIntegerField(default=0)),
                ("content", models.TextField()),
                ("content_hash", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "embedding_model",
                    models.CharField(default="text-embedding-3-large", max_length=100),
                ),
                ("embedding_dimensions", models.PositiveSmallIntegerField(default=1536)),
                (
                    "embedding",
                    pgvector.django.vector.VectorField(blank=True, dimensions=1536, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("source_key", "chunk_index"),
                "indexes": [
                    models.Index(fields=["content_hash"], name="assistant_k_content_a8bf8e_idx")
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_key", "chunk_index"),
                        name="unique_knowledge_source_chunk",
                    )
                ],
            },
        ),
    ]
