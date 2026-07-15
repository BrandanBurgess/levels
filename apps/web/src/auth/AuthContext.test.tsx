import type { LevelsClient } from "@levels/api-client";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearAccessToken, getAccessToken, setAccessToken } from "../api/tokenStore";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "./context";

const user = {
  id: "user-1",
  email: "athlete@example.com",
  display_name: "Avery Athlete",
  role: "member" as const,
  account_status: "active" as const,
  timezone: "America/Toronto",
  preferred_units: "metric" as const,
};

function Probe() {
  const { error, isAuthenticated, isRestoring, login, logout, register, user: currentUser } = useAuth();
  return <div><p>{isRestoring ? "Restoring" : isAuthenticated ? currentUser?.email : "Guest"}</p>{error ? <p role="alert">{error}</p> : null}<button onClick={() => void login("athlete@example.com", "very-secure")} type="button">Login</button><button onClick={() => void register?.({ displayName: "Avery Athlete", email: "athlete@example.com", password: "very-secure", preferredUnits: "metric", timezone: "America/Toronto" })} type="button">Register</button><button onClick={() => void logout()} type="button">Logout</button></div>;
}

afterEach(() => clearAccessToken());

describe("AuthProvider", () => {
  it("signs in with email and keeps the bearer token in memory", async () => {
    const POST = vi.fn().mockResolvedValue({ data: { access_token: "secret-token", token_type: "Bearer", expires_in: 900, user } });
    const client = { POST } as unknown as LevelsClient;
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    render(<AuthProvider client={client}><Probe /></AuthProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await screen.findByText("athlete@example.com");
    expect(POST).toHaveBeenCalledWith("/auth/login", { body: { email: "athlete@example.com", password: "very-secure" } });
    expect(getAccessToken()).toBe("secret-token");
    expect(storageSpy).not.toHaveBeenCalled();
    storageSpy.mockRestore();
  });

  it("restores an in-memory session through auth me", async () => {
    setAccessToken("existing-token");
    const GET = vi.fn().mockResolvedValue({ data: user });
    render(<AuthProvider client={{ GET } as unknown as LevelsClient}><Probe /></AuthProvider>);

    expect(screen.getByText("Restoring")).toBeInTheDocument();
    await screen.findByText("athlete@example.com");
    expect(GET).toHaveBeenCalledWith("/auth/me");
  });

  it("registers every contract field and authenticates the new member", async () => {
    const POST = vi.fn().mockResolvedValue({ data: { access_token: "new-token", token_type: "Bearer", expires_in: 900, user } });
    render(<AuthProvider client={{ POST } as unknown as LevelsClient}><Probe /></AuthProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await screen.findByText("athlete@example.com");
    expect(POST).toHaveBeenCalledWith("/auth/register", { body: { display_name: "Avery Athlete", email: "athlete@example.com", password: "very-secure", preferred_units: "metric", timezone: "America/Toronto" } });
    expect(getAccessToken()).toBe("new-token");
  });

  it("uses a non-enumerating duplicate registration message", async () => {
    const client = { POST: vi.fn().mockResolvedValue({ error: { error: { code: "conflict", message: "conflict" } }, response: new Response(null, { status: 409 }) }) } as unknown as LevelsClient;
    render(<AuthProvider client={client}><Probe /></AuthProvider>);

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be created with those details");
    expect(screen.getByRole("alert")).not.toHaveTextContent("already exists");
  });

  it("always clears local authentication when logout cannot reach the API", async () => {
    setAccessToken("existing-token");
    const client = {
      GET: vi.fn().mockResolvedValue({ data: user }),
      POST: vi.fn().mockRejectedValue(new Error("offline")),
    } as unknown as LevelsClient;
    render(<AuthProvider client={client}><Probe /></AuthProvider>);
    await screen.findByText("athlete@example.com");

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => expect(screen.getByText("Guest")).toBeInTheDocument());
    expect(getAccessToken()).toBeUndefined();
  });
});
