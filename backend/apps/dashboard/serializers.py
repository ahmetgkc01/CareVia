from rest_framework import serializers

from apps.clinicians.serializers import ClinicianSummarySerializer


class DashboardSummarySerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=("staff", "patient"), read_only=True)
    total_patients = serializers.IntegerField(read_only=True)
    upcoming_appointments = serializers.IntegerField(read_only=True)
    active_clinicians = serializers.IntegerField(read_only=True)
    active_doctors = serializers.IntegerField(read_only=True)
    active_nurses = serializers.IntegerField(read_only=True)
    care_team = ClinicianSummarySerializer(many=True, read_only=True)


class ReleaseCommitSerializer(serializers.Serializer):
    sha = serializers.CharField(read_only=True)
    committed_at = serializers.DateTimeField(read_only=True)
    message = serializers.CharField(read_only=True)


class ReleaseOverviewSerializer(serializers.Serializer):
    release = serializers.CharField(read_only=True)
    repository_url = serializers.URLField(read_only=True)
    changelog_url = serializers.URLField(read_only=True)
    commits = ReleaseCommitSerializer(many=True, read_only=True)
