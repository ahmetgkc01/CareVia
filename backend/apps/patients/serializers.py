from django.db import transaction
from rest_framework import serializers

from .models import Allergy, Patient


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = ("id", "allergen", "reaction", "severity", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class PatientSerializer(serializers.ModelSerializer):
    allergies = AllergySerializer(many=True, required=False)

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
            "allergy_status",
            "allergies",
            "clinical_notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def validate(self, attrs):
        status = attrs.get(
            "allergy_status",
            self.instance.allergy_status if self.instance else Patient.AllergyStatus.UNKNOWN,
        )
        allergies = attrs.get("allergies")
        if status == Patient.AllergyStatus.CONFIRMED:
            has_allergies = (
                bool(allergies)
                if allergies is not None
                else bool(self.instance and self.instance.allergies.exists())
            )
            if not has_allergies:
                raise serializers.ValidationError(
                    {
                        "allergies": (
                            "At least one allergy is required when allergy status is confirmed."
                        )
                    }
                )
        if status != Patient.AllergyStatus.CONFIRMED and allergies:
            raise serializers.ValidationError(
                {"allergies": "Allergy records require a confirmed allergy status."}
            )
        if allergies is not None:
            allergen_names = [allergy["allergen"].casefold() for allergy in allergies]
            if len(allergen_names) != len(set(allergen_names)):
                raise serializers.ValidationError(
                    {"allergies": "Duplicate allergens are not allowed for the same patient."}
                )
        return attrs

    @staticmethod
    def _replace_allergies(patient, allergies):
        patient.allergies.all().delete()
        Allergy.objects.bulk_create(
            Allergy(patient=patient, **allergy) for allergy in allergies
        )

    @transaction.atomic
    def create(self, validated_data):
        allergies = validated_data.pop("allergies", [])
        patient = super().create(validated_data)
        if allergies:
            self._replace_allergies(patient, allergies)
        return patient

    @transaction.atomic
    def update(self, instance, validated_data):
        allergies = validated_data.pop("allergies", None)
        patient = super().update(instance, validated_data)
        if patient.allergy_status != Patient.AllergyStatus.CONFIRMED:
            self._replace_allergies(patient, [])
        elif allergies is not None:
            self._replace_allergies(patient, allergies)
        return patient


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
            if field not in {"allergy_status", "allergies", "clinical_notes"}
        )

