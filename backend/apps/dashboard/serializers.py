from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=("staff", "patient"), read_only=True)
    total_patients = serializers.IntegerField(read_only=True)
    upcoming_appointments = serializers.IntegerField(read_only=True)
    active_clinicians = serializers.IntegerField(read_only=True)
    active_doctors = serializers.IntegerField(read_only=True)
    active_nurses = serializers.IntegerField(read_only=True)
