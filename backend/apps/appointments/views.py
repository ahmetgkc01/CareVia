from rest_framework.viewsets import ModelViewSet

from .models import Appointment
from .permissions import STAFF_GROUPS, AppointmentPermission
from .serializers import AppointmentPublicSerializer, AppointmentSerializer


class AppointmentViewSet(ModelViewSet):
    permission_classes = (AppointmentPermission,)
    lookup_field = "public_id"
    filterset_fields = ("status", "patient__public_id", "clinician__public_id")
    search_fields = ("patient__first_name", "patient__last_name", "reason")
    ordering_fields = ("start_at", "end_at", "created_at")

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related("patient", "clinician__user")
        if user.is_superuser:
            return queryset
        groups = set(user.groups.values_list("name", flat=True))
        if groups & STAFF_GROUPS:
            return queryset
        if "Patient" in groups:
            return queryset.filter(patient__user=user)
        return queryset.none()

    def get_serializer_class(self):
        groups = set(self.request.user.groups.values_list("name", flat=True))
        if groups & {"Patient", "Secretary", "Auditor"} and not self.request.user.is_superuser:
            return AppointmentPublicSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

