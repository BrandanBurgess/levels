import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./api/client";
import { clearAccessToken, setAccessToken } from "./api/tokenStore";
import { App } from "./App";
import { EmptyState, ErrorState, LoadingState } from "./ui/AsyncState";

describe("App shell", () => {
  it("renders the guest landing page without the member shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Progress feels better when the plan can move with you." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Try demo" })).toHaveAttribute("href", "#/demo");
    expect(screen.queryByRole("navigation", { name: "Primary navigation" })).not.toBeInTheDocument();
  });

  it("restores a member and routes inside the accessible shell", async () => {
    setAccessToken("member-token");
    window.location.hash = "#/journal";
    vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
      if (path === "/auth/me") return { data: { id: "user-1", email: "member@example.com", display_name: "Alex", role: "member", account_status: "active", timezone: "America/Toronto", preferred_units: "metric" }, response: new Response() } as never;
      if (path === "/today") return { data: { effective_day: null, schedule_version: 1 }, response: new Response() } as never;
      return { data: [], response: new Response() } as never;
    });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Journal" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Mobile navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute("href", "#main-content");

    fireEvent.click(screen.getAllByRole("link", { name: "More" })[0]!);
    expect(screen.getByRole("heading", { name: "More" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Library/ }).length).toBeGreaterThan(0);
  });
});

afterEach(() => {
  clearAccessToken();
  window.location.hash = "";
  vi.restoreAllMocks();
});

describe("shared async states", () => {
  it("announces loading, errors, retries, and empty content", () => {
    let retried = false;
    const { rerender } = render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Waking up your training data…");

    rerender(<ErrorState message="Training data is unavailable." onRetry={() => (retried = true)} />);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retried).toBe(true);

    rerender(<EmptyState title="No sessions yet">Your first workout will appear here.</EmptyState>);
    expect(screen.getByRole("heading", { name: "No sessions yet" })).toBeInTheDocument();
  });
});
