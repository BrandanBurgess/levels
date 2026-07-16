import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthState } from "./context";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";

function state(overrides: Partial<AuthState> = {}): AuthState {
  return {
    isAuthenticated: false,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(async () => undefined),
    ...overrides,
  };
}

describe("account forms", () => {
  it("uses an email login and a generic credential error", () => {
    render(<MemoryRouter><AuthContext.Provider value={state({ error: "Sign in failed. Check your credentials and try again." })}><LoginPage /></AuthContext.Provider></MemoryRouter>);
    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByRole("alert")).toHaveTextContent("Sign in failed");
  });

  it("requires terms acceptance and submits all contract account fields", async () => {
    const register = vi.fn(async () => false);
    render(<MemoryRouter><AuthContext.Provider value={state({ register })}><RegisterPage /></AuthContext.Provider></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Avery" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "avery@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "ten-characters" } });
    fireEvent.click(screen.getByLabelText(/basic terms and privacy notice/i));
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(register).toHaveBeenCalledWith(expect.objectContaining({ displayName: "Avery", email: "avery@example.com", password: "ten-characters", preferredUnits: "metric" }));
  });

  it("explains that starter setup can take a few seconds", () => {
    render(<MemoryRouter><AuthContext.Provider value={state({ isSubmitting: true })}><RegisterPage /></AuthContext.Provider></MemoryRouter>);

    expect(screen.getByRole("status")).toHaveTextContent("starter plan");
    expect(screen.getByRole("button", { name: /Creating account/ })).toBeDisabled();
  });
});
