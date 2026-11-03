import { apiRequest } from "../../shared/api/client";

export type DashboardSummary = {
  scope: "staff" | "patient";
  total_patients: number;
  upcoming_appointments: number;
  active_clinicians: number;
  active_doctors: number;
  active_nurses: number;
  care_team: Array<{
    public_id: string;
    display_name: string;
    profession: "doctor" | "nurse";
    specialty: string;
  }>;
};

export type HealthStatus = {
  status: "ok";
  release: string;
};

export type ReleaseOverview = {
  release: string;
  repository_url: string;
  changelog_url: string;
  commits: Array<{
    sha: string;
    committed_at: string;
    message: string;
  }>;
};

export const dashboardApi = {
  summary: () => apiRequest<DashboardSummary>("/api/dashboard/summary/"),
  health: () => apiRequest<HealthStatus>("/api/health/"),
  release: () => apiRequest<ReleaseOverview>("/api/release/"),
};

