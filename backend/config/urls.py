from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


@require_GET
def health_check(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/session/", include("apps.accounts.urls")),
    path("api/", include("apps.accounts.api_urls")),
    path("api/", include("apps.dashboard.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/", include("apps.clinicians.urls")),
    path("api/", include("apps.patients.urls")),
    path("api/", include("apps.appointments.urls")),
    path("api/", include("apps.assistant.urls")),
]

