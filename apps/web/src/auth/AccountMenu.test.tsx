import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AccountMenu } from "./AccountMenu";
import { AuthContext, type AuthState } from "./context";

describe("AccountMenu", () => {
  it("shows email, account status, and signs out", () => {
    const logout = vi.fn(async () => undefined);
    const auth: AuthState = {
      user: { id: "u1", email: "member@example.com", display_name: "Member", role: "member", account_status: "active", timezone: "America/Toronto", preferred_units: "metric" },
      admin: { displayName: "Member" },
      isAuthenticated: true,
      isSubmitting: false,
      login: vi.fn(async () => false),
      logout,
    };
    const { container } = render(<MemoryRouter><AuthContext.Provider value={auth}><AccountMenu /></AuthContext.Provider></MemoryRouter>);

    fireEvent.click(container.querySelector("summary")!);
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(logout).toHaveBeenCalledOnce();
  });
});
