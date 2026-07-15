import { describe, expect, it, vi } from "vitest";

import { createLevelsClient } from "./index";

describe("createLevelsClient", () => {
  it("calls a typed API path with a normalized base URL", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", version: "test", database: "ok" }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    const client = createLevelsClient({
      baseUrl: "https://api.example.test/api/v1/",
      fetch: fetchMock,
    });

    const { data, error } = await client.GET("/health");

    expect(error).toBeUndefined();
    expect(data?.status).toBe("ok");
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toMatchObject({
      url: "https://api.example.test/api/v1/health",
    });
  });

  it("adds the current bearer token without storing credentials", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "profile", display_name: "Brandan" }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    const client = createLevelsClient({
      baseUrl: "https://api.example.test/api/v1",
      fetch: fetchMock,
      getAccessToken: () => "short-lived-token",
    });

    await client.GET("/me/profile");

    const request = fetchMock.mock.calls[0]?.[0];
    expect(request).toBeInstanceOf(Request);
    expect((request as Request).headers.get("Authorization")).toBe(
      "Bearer short-lived-token",
    );
  });
});
