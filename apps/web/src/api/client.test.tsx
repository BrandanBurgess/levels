import type { LevelsClient } from "@levels/api-client";
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import { useAuth } from "../auth/context";
import { createColdStartFetch } from "./client";
import { clearAccessToken, getAccessToken } from "./tokenStore";

afterEach(() => clearAccessToken());

describe("cold-start fetch", () => {
  it("retries bounded GET failures", async () => {
    const fetchImplementation = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }));
    const wrapped = createColdStartFetch(fetchImplementation, {
      retries: 2,
      timeoutMs: 100,
      delay: async () => undefined,
    });

    const response = await wrapped("https://api.example.test/dashboard");
    expect(response.status).toBe(200);
    expect(fetchImplementation).toHaveBeenCalledTimes(2);
  });

  it("never retries writes", async () => {
    const fetchImplementation = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 503 }));
    const wrapped = createColdStartFetch(fetchImplementation, {
      retries: 2,
      delay: async () => undefined,
    });

    const response = await wrapped("https://api.example.test/water", { method: "POST" });
    expect(response.status).toBe(503);
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
  });
});

function AuthProbe() {
  const { admin, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <p>{isAuthenticated ? admin?.displayName : "Public"}</p>
      <button onClick={() => void login("brandan", "password")} type="button">
        Login
      </button>
      <button onClick={logout} type="button">
        Logout
      </button>
    </div>
  );
}

describe("memory-only auth", () => {
  it("stores the access token only in module memory and clears it on logout", async () => {
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    const client = {
      POST: vi.fn().mockResolvedValue({
        data: {
          access_token: "memory-token",
          expires_in_seconds: 900,
          admin: { display_name: "Brandan Burgess" },
        },
      }),
    } as unknown as LevelsClient;
    render(
      <AuthProvider client={client}>
        <AuthProbe />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Login" }));
    await waitFor(() => expect(screen.getByText("Brandan Burgess")).toBeInTheDocument());
    expect(getAccessToken()).toBe("memory-token");
    expect(storageSpy).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));
    expect(screen.getByText("Public")).toBeInTheDocument();
    expect(getAccessToken()).toBeUndefined();
    storageSpy.mockRestore();
  });
});
