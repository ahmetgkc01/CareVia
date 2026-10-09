import { apiRequest } from "../../shared/api/client";

export type DashboardSummary = {
  scope: "staff" | "patient";
  total_patients: number;
  upcoming_appointments: number;
  active_clinicians: number;
  active_doctors: number;
  active_nurses: number;
};

export type HealthStatus = {
  status: "ok";
  release: string;
};

export const dashboardApi = {
  summary: () => apiRequest<DashboardSummary>("/api/dashboard/summary/"),
  health: () => apiRequest<HealthStatus>("/api/health/"),
};

