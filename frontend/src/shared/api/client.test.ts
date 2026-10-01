import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("apiRequest", () => {
  it("sends session credentials and returns JSON", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiRequest<{ status: string }>("/api/health/")).resolves.toEqual({
      status: "ok",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health/",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("raises an ApiError with the server detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Forbidden" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiRequest("/api/private/")).rejects.toEqual(
      expect.objectContaining({ status: 403, message: "Forbidden" }),
    );
  });
});
