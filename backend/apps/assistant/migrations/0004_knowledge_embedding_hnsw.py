from django.db import migrations
from pgvector.django import HnswIndex


INDEX_NAME = "knowledge_embedding_hnsw"


def create_postgres_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
            "ON assistant_knowledgechunk USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )


def drop_postgres_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")


class Migration(migrations.Migration):
    dependencies = [("assistant", "0003_alter_knowledgechunk_embedding_model")]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddIndex(
                    model_name="knowledgechunk",
                    index=HnswIndex(
                        name=INDEX_NAME,
                        fields=("embedding",),
                        m=16,
                        ef_construction=64,
                        opclasses=("vector_cosine_ops",),
                    ),
                )
            ],
            database_operations=[
                migrations.RunPython(create_postgres_index, drop_postgres_index)
            ],
        )
    ]
