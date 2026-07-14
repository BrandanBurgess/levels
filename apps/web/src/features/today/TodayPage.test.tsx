import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
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

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TodayPage />
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
});
