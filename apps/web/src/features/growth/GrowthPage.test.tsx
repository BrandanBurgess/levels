import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { GrowthPage } from "./GrowthPage";

type Suggestion = components["schemas"]["GrowthSuggestion"];

const increase: Suggestion = {
  exercise_id: "incline_press",
  exercise_name: "Incline Press",
  suggestion_type: "increase_load",
  suggested_delta: 1.133981,
  delta_unit: "kg",
  confidence: "high",
  explanation: [
    "All 3 latest working sets reached 8 reps.",
    "Use only the smallest configured load increment; no max attempt is suggested.",
  ],
  source_session_ids: ["abcdef01-session", "abcdef02-session"],
};

const insufficient: Suggestion = {
  exercise_id: "pull_up",
  exercise_name: "Pull-Up",
  suggestion_type: "insufficient_data",
  confidence: "insufficient",
  explanation: ["1 comparable completed session found; at least 2 are required."],
  source_session_ids: ["session-one"],
};

function renderPage(isAuthenticated: boolean, data: Suggestion[] = [increase, insufficient], units: "metric" | "imperial" = "metric") {
  vi.spyOn(apiClient, "GET").mockResolvedValue({ data, response: new Response() });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth: AuthState = {
    ...(isAuthenticated ? { admin: { displayName: "Brandan" } } : {}),
    ...(isAuthenticated ? { user: { id: "user-1", email: "member@example.com", display_name: "Brandan", role: "member" as const, account_status: "active" as const, timezone: "America/Toronto", preferred_units: units } } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={auth}>
        <QueryClientProvider client={queryClient}>
          <GrowthPage />
        </QueryClientProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("GrowthPage", () => {
  it("shows public action, confidence, reasoning, and cited evidence", async () => {
    renderPage(false);

    expect(await screen.findByRole("heading", { name: "Incline Press" })).toBeInTheDocument();
    expect(screen.getByText("Increase by 1.13 kg")).toBeInTheDocument();
    expect(screen.getByLabelText("high confidence")).toBeInTheDocument();
    expect(screen.getByText(/smallest configured load increment/)).toBeInTheDocument();
    expect(screen.getByText("Session 1 · abcdef01")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use suggestion" })).not.toBeInTheDocument();
    expect(screen.getByText("Build more history")).toBeInTheDocument();
  });

  it("lets the owner retain a suggestion for the next workout", async () => {
    renderPage(true, [increase]);
    fireEvent.click(await screen.findByRole("button", { name: "Use suggestion" }));

    expect(screen.getByRole("status")).toHaveTextContent("Saved for the next workout.");
    const stored = sessionStorage.getItem("levels:growth:accepted:incline_press");
    expect(stored).toContain('"suggestion_type":"increase_load"');
    expect(screen.getByRole("link", { name: "Open Journal" })).toHaveAttribute(
      "href",
      "/journal",
    );
  });

  it("shows kilogram deltas in the owner's persisted imperial preference", async () => {
    renderPage(true, [increase], "imperial");

    expect(await screen.findByText("Increase by 2.5 lb")).toBeInTheDocument();
  });

  it("requests guidance for a selected training date", async () => {
    renderPage(false, [increase]);
    await screen.findByRole("heading", { name: "Incline Press" });
    fireEvent.change(screen.getByLabelText("Training date"), {
      target: { value: "2026-07-14" },
    });

    await waitFor(() =>
      expect(apiClient.GET).toHaveBeenLastCalledWith("/growth/suggestions", {
        params: { query: { date: "2026-07-14" } },
      }),
    );
  });

  it("explains an empty visible state without inventing a score", async () => {
    renderPage(false, []);
    expect(await screen.findByRole("heading", { name: "No visible guidance" })).toBeInTheDocument();
    expect(screen.queryByText(/fitness score/i)).not.toBeInTheDocument();
  });
});
