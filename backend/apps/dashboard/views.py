from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.clinicians.models import Clinician
from apps.patients.models import Patient

from .serializers import DashboardSummarySerializer

STAFF_GROUPS = {"Admin", "Doctor", "Nurse", "Secretary", "Auditor"}
UPCOMING_STATUSES = {Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED}


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

