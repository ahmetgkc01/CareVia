import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "../auth/api";
import { patientApi } from "../patients/api";
import { AssistantPage } from "./AssistantPage";
import { assistantApi } from "./api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, values?: { prompt?: string }) => (
      key === "assistantPendingPatientPrompt"
        ? `${values?.prompt} pending patient selection`
        : key
    ),
    i18n: { resolvedLanguage: "tr" },
  }),
}));

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  vi.spyOn(authApi, "me").mockResolvedValue({
    id: 1,
    username: "doctor",
    email: "doctor@example.test",
    first_name: "Ada",
    last_name: "Example",
    is_superuser: false,
    groups: ["Doctor"],
  });
  vi.spyOn(patientApi, "list").mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [{
      public_id: "patient-1",
      first_name: "Grace",
      last_name: "Hopper",
      birth_date: "1980-01-01",
      gender: "female",
      email: "grace@example.test",
      phone: "",
      address: "",
      country_code: "TR",
      preferred_language: "tr",
      emergency_contact_name: "",
      emergency_contact_phone: "",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }],
  });
  vi.spyOn(assistantApi, "history").mockResolvedValue([]);
  vi.spyOn(assistantApi, "send").mockResolvedValue({
    id: 1,
    role: "assistant",
    content: "Randevu bulundu.",
    category: "appointments",
    safety_code: "",
    sources: [],
    created_at: "2026-01-01T00:00:00Z",
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AssistantPage />
    </QueryClientProvider>,
  );
}

describe("AssistantPage quick prompts", () => {
  it("sends a population allergy prompt without selecting a patient", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("assistantPromptAllergyPatients"));

    await waitFor(() => {
      expect(vi.mocked(assistantApi.send).mock.calls[0]?.[0]).toEqual({
        message: "assistantPromptAllergyPatients",
        language: "tr",
      });
    });
  });

  it("queues a doctor prompt and sends it automatically after patient selection", async () => {
    renderPage();

    fireEvent.click(await screen.findByText("assistantPromptAppointments"));

    expect(assistantApi.send).not.toHaveBeenCalled();
    expect(screen.getByText(/pending patient selection/)).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("combobox", { name: "assistantPatientContext" }));
    fireEvent.click(await screen.findByRole("option", { name: "Grace Hopper" }));

    await waitFor(() => {
      expect(vi.mocked(assistantApi.send).mock.calls[0]?.[0]).toEqual({
        message: "assistantPromptAppointments",
        language: "tr",
        patient_id: "patient-1",
      });
    });
    expect(patientApi.list).toHaveBeenCalledWith("", 1);
  });
});
