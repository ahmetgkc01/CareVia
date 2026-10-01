from rest_framework.viewsets import ModelViewSet

from .models import Patient
from .permissions import STAFF_GROUPS, PatientAccessPermission
from .serializers import PatientOperationalSerializer, PatientSelfSerializer, PatientSerializer


class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = (PatientAccessPermission,)
    lookup_field = "public_id"
    filterset_fields = ("gender", "country_code", "preferred_language", "is_active")
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering_fields = ("first_name", "last_name", "birth_date", "created_at")

    def get_serializer_class(self):
        user = self.request.user
        groups = set(user.groups.values_list("name", flat=True))
        if "Patient" in groups and not user.is_superuser:
            return PatientSelfSerializer
        if groups & {"Secretary", "Auditor"} and not user.is_superuser:
            return PatientOperationalSerializer
        return PatientSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Patient.objects.select_related("user")
        if user.is_superuser:
            return queryset
        groups = set(user.groups.values_list("name", flat=True))
        if groups & STAFF_GROUPS:
            return queryset
        if "Patient" in groups:
            return queryset.filter(user=user)
        return queryset.none()

