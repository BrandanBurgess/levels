import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LandingPage } from "./LandingPage";

describe("LandingPage", () => {
  it("offers demo, sign in, and account creation without exposing member data", () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: /Progress feels better/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Try demo" })).toHaveAttribute("href", "/demo");
    expect(screen.getAllByRole("link", { name: "Sign in" })[0]).toHaveAttribute("href", "/login");
    expect(screen.getAllByRole("link", { name: "Create account" }).length).toBeGreaterThan(0);
    expect(screen.getByText(/training data stays private/i)).toBeInTheDocument();
  });
});
