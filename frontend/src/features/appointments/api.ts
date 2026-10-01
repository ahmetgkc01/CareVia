import { apiRequest } from "../../shared/api/client";

export type AppointmentStatus = "scheduled" | "confirmed" | "completed" | "cancelled" | "no_show";

export type Appointment = {
  public_id: string;
  patient: { public_id: string; first_name: string; last_name: string };
  clinician: { public_id: string; display_name: string; profession: string; specialty: string };
  start_at: string;
  end_at: string;
  status: AppointmentStatus;
  reason: string;
  internal_notes?: string;
  created_at: string;
  updated_at: string;
};

export type AppointmentInput = {
  patient_id: string;
  clinician_id: string;
  start_at: string;
  end_at: string;
  status: AppointmentStatus;
  reason: string;
  internal_notes?: string;
};

type PaginatedAppointments = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Appointment[];
};

export const appointmentApi = {
  list: (status: string, page: number) => {
    const params = new URLSearchParams({ page: String(page), ordering: "start_at" });
    if (status) params.set("status", status);
    return apiRequest<PaginatedAppointments>(`/api/appointments/?${params}`);
  },
  create: (appointment: AppointmentInput) =>
    apiRequest<Appointment>("/api/appointments/", {
      method: "POST",
      body: JSON.stringify(appointment),
    }),
  update: (publicId: string, appointment: Partial<AppointmentInput>) =>
    apiRequest<Appointment>(`/api/appointments/${publicId}/`, {
      method: "PATCH",
      body: JSON.stringify(appointment),
    }),
};

