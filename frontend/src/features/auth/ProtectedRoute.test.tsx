import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./ProtectedRoute";
import { authApi } from "./api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderRoute() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/private"]}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/private" element={<div>private page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("renders protected content for an authenticated user", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({
      id: 1,
      username: "doctor",
      email: "doctor@example.test",
      first_name: "Ada",
      last_name: "Example",
      groups: ["Doctor"],
    });

    renderRoute();

    expect(await screen.findByText("private page")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to login", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(new Error("Unauthorized"));

    renderRoute();

    expect(await screen.findByText("login page")).toBeInTheDocument();
  });
});
