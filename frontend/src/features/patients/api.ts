import { apiRequest } from "../../shared/api/client";

export type Patient = {
  public_id: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  gender: "female" | "male" | "non_binary" | "other" | "undisclosed" | "";
  email: string;
  phone: string;
  address: string;
  country_code: string;
  preferred_language: "tr" | "en";
  emergency_contact_name: string;
  emergency_contact_phone: string;
  allergies?: string;
  clinical_notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PatientInput = Omit<Patient, "public_id" | "created_at" | "updated_at">;

type PaginatedPatients = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Patient[];
};

export const patientApi = {
  list: (search: string, page: number, pageSize = 25) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      ordering: "last_name,first_name",
    });
    if (search) params.set("search", search);
    return apiRequest<PaginatedPatients>(`/api/patients/?${params}`);
  },
  create: (patient: PatientInput) =>
    apiRequest<Patient>("/api/patients/", { method: "POST", body: JSON.stringify(patient) }),
  update: (publicId: string, patient: Partial<PatientInput>) =>
    apiRequest<Patient>(`/api/patients/${publicId}/`, {
      method: "PATCH",
      body: JSON.stringify(patient),
    }),
};

