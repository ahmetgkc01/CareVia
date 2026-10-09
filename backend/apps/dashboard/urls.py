from django.urls import path

from .views import DashboardSummaryView, ReleaseOverviewView

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("release/", ReleaseOverviewView.as_view(), name="release-overview"),
]

