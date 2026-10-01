from rest_framework.viewsets import ModelViewSet

from .models import Clinician
from .permissions import ClinicianPermission
from .serializers import ClinicianSerializer


class ClinicianViewSet(ModelViewSet):
    serializer_class = ClinicianSerializer
    permission_classes = (ClinicianPermission,)
    lookup_field = "public_id"
    filterset_fields = ("profession", "specialty", "country_code", "is_active")
    search_fields = ("user__first_name", "user__last_name", "user__email", "specialty")
    ordering_fields = ("user__first_name", "user__last_name", "profession", "specialty")

    def get_queryset(self):
        return Clinician.objects.select_related("user")

