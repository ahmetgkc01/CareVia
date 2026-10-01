from rest_framework import serializers

from apps.clinicians.models import Clinician
from apps.clinicians.serializers import ClinicianSummarySerializer
from apps.patients.models import Patient

from .models import Appointment


class PatientSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("public_id", "first_name", "last_name")


class AppointmentSerializer(serializers.ModelSerializer):
    patient_id = serializers.SlugRelatedField(
        source="patient",
        slug_field="public_id",
        queryset=Patient.objects.filter(is_active=True),
        write_only=True,
    )
    clinician_id = serializers.SlugRelatedField(
        source="clinician",
        slug_field="public_id",
        queryset=Clinician.objects.filter(is_active=True),
        write_only=True,
    )
    patient = PatientSummarySerializer(read_only=True)
    clinician = ClinicianSummarySerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "public_id",
            "patient_id",
            "patient",
            "clinician_id",
            "clinician",
            "start_at",
            "end_at",
            "status",
            "reason",
            "internal_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def validate(self, attrs):
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        clinician = attrs.get("clinician", getattr(self.instance, "clinician", None))
        status_value = attrs.get(
            "status",
            getattr(self.instance, "status", Appointment.Status.SCHEDULED),
        )
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError({"end_at": "End time must be after start time."})
        blocking_statuses = (Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED)
        if clinician and start_at and end_at and status_value in blocking_statuses:
            conflicts = Appointment.objects.filter(
                clinician=clinician,
                status__in=blocking_statuses,
                start_at__lt=end_at,
                end_at__gt=start_at,
            )
            if self.instance:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise serializers.ValidationError(
                    "The clinician already has an appointment in this period."
                )
        return attrs


class AppointmentPublicSerializer(AppointmentSerializer):
    class Meta(AppointmentSerializer.Meta):
        fields = tuple(
            field for field in AppointmentSerializer.Meta.fields if field != "internal_notes"
        )

