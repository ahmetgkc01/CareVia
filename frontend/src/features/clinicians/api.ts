import { apiRequest } from "../../shared/api/client";

export type Clinician = {
  public_id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  profession: "doctor" | "nurse";
  specialty: string;
  country_code: string;
  is_active: boolean;
};

type PaginatedClinicians = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Clinician[];
};

export type ClinicianInput = Omit<Clinician, "public_id"> & { password?: string };

export const clinicianApi = {
  list: (search = "") => {
    const params = new URLSearchParams({ page_size: "100", ordering: "user__last_name" });
    if (search) params.set("search", search);
    return apiRequest<PaginatedClinicians>(`/api/clinicians/?${params}`);
  },
  create: (payload: ClinicianInput) =>
    apiRequest<Clinician>("/api/clinicians/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (publicId: string, payload: ClinicianInput) =>
    apiRequest<Clinician>(`/api/clinicians/${publicId}/`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
};

