from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = (
            "public_id",
            "first_name",
            "last_name",
            "birth_date",
            "gender",
            "email",
            "phone",
            "address",
            "country_code",
            "preferred_language",
            "emergency_contact_name",
            "emergency_contact_phone",
            "allergies",
            "clinical_notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class PatientSelfSerializer(PatientSerializer):
    class Meta(PatientSerializer.Meta):
        fields = tuple(
            field for field in PatientSerializer.Meta.fields if field != "clinical_notes"
        )


class PatientOperationalSerializer(PatientSerializer):
    class Meta(PatientSerializer.Meta):
        fields = tuple(
            field
            for field in PatientSerializer.Meta.fields
            if field not in {"allergies", "clinical_notes"}
        )

