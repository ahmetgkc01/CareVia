from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0002_knowledgechunk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgechunk",
            name="embedding_model",
            field=models.CharField(default="text-embedding-3-small", max_length=100),
        ),
    ]
