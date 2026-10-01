from rest_framework import serializers

from .models import AssistantMessage


class AssistantRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    language = serializers.ChoiceField(choices=("tr", "en"), default="tr")
    patient_id = serializers.UUIDField(required=False, allow_null=True)


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = (
            "id",
            "role",
            "content",
            "category",
            "safety_code",
            "sources",
            "created_at",
        )
        read_only_fields = fields
