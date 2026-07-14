import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext } from "../../auth/context";
import { TodayPage } from "./TodayPage";

const dashboard = {
  date: "2026-07-13",
  profile: {
    display_name: "Brandan Burgess",
    preferred_units: "imperial" as const,
    timezone: "America/Toronto",
    avatar_variant: "default",
  },
  scheduled_day: {
    id: "upper-a",
    name: "Upper A — Incline + Back",
    day_type: "upper",
    sequence: 1,
    is_optional: false,
    items: [
      {
        id: "incline-press-item",
        exercise: {
          id: "incline-press",
          slug: "incline-dumbbell-press",
          name: "Incline Dumbbell Press",
          aliases: [],
          variation_group: "incline-press",
          movement_pattern: "horizontal-push",
          equipment: "dumbbell",
          measurement_type: "load_reps" as const,
          compound: true,
          unilateral: false,
          automatic_progression_enabled: true,
          muscle_targets: [],
        },
        sequence: 1,
        item_type: "main" as const,
        sets: 3,
        rep_min: 8,
        rep_max: 12,
        optional: false,
        alternatives: [],
      },
    ],
  },
  active_session: null,
  muscle_targets: [
    {
      slug: "upper-chest",
      display_name: "Upper Chest",
      role: "primary" as const,
      intensity: 1,
      svg_region_ids: ["chest-upper"],
    },
  ],
  water: null,
  latest_achievements: [],
};

function renderPage(isAuthenticated = false) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider
        value={{
          ...(isAuthenticated ? { admin: { displayName: "Brandan Burgess" } } : {}),
          isAuthenticated,
          isSubmitting: false,
          login: vi.fn(async () => false),
          logout: vi.fn(),
        }}
      >
        <TodayPage />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("TodayPage", () => {
  it("renders live plan, muscle, and privacy-safe hydration data", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: dashboard, response: new Response() });

    renderPage();

    expect(screen.getByRole("status")).toHaveTextContent("Waking up your training data");
    expect(await screen.findByRole("heading", { name: "Ready for Upper A" })).toBeInTheDocument();
    expect(screen.getByText("Incline Dumbbell Press")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent(
      "Upper Chest",
    );
    expect(screen.getByRole("heading", { name: "Private" })).toBeInTheDocument();
  });

  it("announces an API error and retries on request", async () => {
    const getDashboard = vi
      .spyOn(apiClient, "GET")
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: dashboard, response: new Response() });

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Training data could not be loaded");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(getDashboard).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Incline Dumbbell Press")).toBeInTheDocument();
  });

  it("lets the owner quick-add and undo water", async () => {
    const ownerDashboard = {
      ...dashboard,
      water: {
        local_date: "2026-07-13",
        total_ml: 0,
        goal_ml: 2800,
        progress_ratio: 0,
        entries: [],
      },
    };
    vi.spyOn(apiClient, "GET").mockResolvedValue({
      data: ownerDashboard,
      response: new Response(),
    });
    const post = vi
      .spyOn(apiClient, "POST")
      .mockResolvedValueOnce({
        data: {
          ...ownerDashboard.water,
          total_ml: 500,
          progress_ratio: 500 / 2800,
          entries: [
            { id: "water-1", amount_ml: 500, occurred_at: "2026-07-13T16:00:00Z" },
          ],
        },
        response: new Response(),
      })
      .mockResolvedValueOnce({
        data: ownerDashboard.water,
        response: new Response(),
      });

    renderPage(true);

    expect(await screen.findByRole("heading", { name: "0 mL" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "+500 mL" }));
    expect(await screen.findByRole("status")).toHaveTextContent("500 mL added");
    expect(screen.getByRole("heading", { name: "500 mL" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo latest" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Latest water entry undone");
    expect(screen.getByRole("heading", { name: "0 mL" })).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(2);
  });
});
