import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authApi } from "./auth/api";
import { clinicianApi } from "./clinicians/api";
import { ClinicianPage } from "./clinicians/ClinicianPage";
import { patientApi } from "./patients/api";
import { PatientPage } from "./patients/PatientPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

function renderPage(page: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{page}</QueryClientProvider>);
}

beforeEach(() => {
  vi.spyOn(authApi, "me").mockResolvedValue({
    id: 1,
    username: "admin",
    email: "admin@example.test",
    first_name: "Test",
    last_name: "Admin",
    is_superuser: true,
    groups: ["Admin"],
  });
  vi.spyOn(patientApi, "list").mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
  vi.spyOn(clinicianApi, "list").mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("required field feedback", () => {
  it("shows patient field errors and does not submit an empty record", async () => {
    const create = vi.spyOn(patientApi, "create");
    renderPage(<PatientPage />);

    fireEvent.click(await screen.findByRole("button", { name: "addPatient" }));
    const dialog = screen.getByRole("dialog", { name: "addPatient" });
    fireEvent.click(within(dialog).getByRole("button", { name: "save" }));

    await waitFor(() => {
      expect(within(dialog).getAllByText("validationRequired")).toHaveLength(3);
    });
    expect(create).not.toHaveBeenCalled();
  });

  it("shows clinician field errors and does not submit an empty record", async () => {
    const create = vi.spyOn(clinicianApi, "create");
    renderPage(<ClinicianPage />);

    fireEvent.click(await screen.findByRole("button", { name: "addClinician" }));
    const dialog = screen.getByRole("dialog", { name: "addClinician" });
    fireEvent.click(within(dialog).getByRole("button", { name: "save" }));

    await waitFor(() => {
      expect(within(dialog).getAllByText("validationRequired")).toHaveLength(4);
      expect(within(dialog).getByText("validationPasswordMin")).toBeInTheDocument();
    });
    expect(create).not.toHaveBeenCalled();
  });
});
