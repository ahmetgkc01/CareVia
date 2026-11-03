import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0004_knowledge_embedding_hnsw"),
        ("patients", "0002_structured_allergies"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistantmessage",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assistant_messages",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="provider_model",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="input_tokens",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="output_tokens",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="estimated_cost_usd",
            field=models.DecimalField(decimal_places=8, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="latency_ms",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="fallback_used",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="assistantmessage",
            index=models.Index(
                fields=["user", "patient", "created_at"],
                name="assistant_history_context_idx",
            ),
        ),
    ]
