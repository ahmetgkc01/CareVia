import json
import os
import subprocess

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient

from .serializers import DashboardSummarySerializer, ReleaseOverviewSerializer

STAFF_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary", "Auditor"}
UPCOMING_STATUSES = {Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED}


def bundled_commits(limit=6):
    history_path = settings.BASE_DIR / "release_history.json"
    try:
        history = json.loads(history_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []

    current = history.get("current", {})
    commits = []
    if current.get("message") and current.get("committed_at"):
        commits.append(
            {
                "sha": os.getenv("CAREVIA_RELEASE", "development"),
                "committed_at": current["committed_at"],
                "message": current["message"],
            }
        )
    commits.extend(history.get("previous", []))
    return commits[:limit]


def recent_commits(limit=6):
    try:
        result = subprocess.run(  # noqa: S603
            [
                "git",
                "-c",
                f"safe.directory={settings.ROOT_DIR}",
                "log",
                f"-{limit}",
                "--date=iso-strict",
                "--pretty=format:%H%x1f%ad%x1f%s",
            ],
            cwd=settings.ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return bundled_commits(limit)

    commits = []
    for line in result.stdout.splitlines():
        fields = line.split("\x1f", 2)
        if len(fields) == 3:
            commits.append(
                {"sha": fields[0], "committed_at": fields[1], "message": fields[2]}
            )
    return commits or bundled_commits(limit)


class DashboardAccessPermission(BasePermission):
    """Reject authenticated accounts that have no recognised Carevia role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        groups = set(request.user.groups.values_list("name", flat=True))
        return bool(groups & STAFF_GROUPS or "Patient" in groups)


class DashboardSummaryView(APIView):
    permission_classes = (DashboardAccessPermission,)

    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request):
        groups = set(request.user.groups.values_list("name", flat=True))
        patient_scope = "Patient" in groups and not (
            request.user.is_superuser or groups & STAFF_GROUPS
        )
        if patient_scope:
            patients = Patient.objects.filter(user=request.user, is_active=True)
            appointments = Appointment.objects.filter(patient__user=request.user)
            scope = "patient"
        else:
            patients = Patient.objects.filter(is_active=True)
            appointments = Appointment.objects.all()
            scope = "staff"

        upcoming_appointments = appointments.filter(
            start_at__gte=timezone.now(),
            status__in=UPCOMING_STATUSES,
        ).count()
        return Response(
            {
                "scope": scope,
                "total_patients": patients.count(),
                "upcoming_appointments": upcoming_appointments,
                "active_clinicians": Clinician.objects.filter(is_active=True).count(),
                "active_doctors": Clinician.objects.filter(
                    is_active=True,
                    profession=Clinician.Profession.DOCTOR,
                ).count(),
                "active_nurses": Clinician.objects.filter(
                    is_active=True,
                    profession=Clinician.Profession.NURSE,
                ).count(),
            }
        )


class ReleaseOverviewView(APIView):
    permission_classes = (DashboardAccessPermission,)

    @extend_schema(responses={200: ReleaseOverviewSerializer})
    def get(self, request):
        repository_url = os.getenv(
            "CAREVIA_REPOSITORY_URL", "https://github.com/ahmetgokce89/CareVia"
        ).rstrip("/")
        return Response(
            {
                "release": os.getenv("CAREVIA_RELEASE", "development"),
                "repository_url": repository_url,
                "changelog_url": f"{repository_url}/blob/main/CHANGELOG.md",
                "commits": recent_commits(),
            }
        )

