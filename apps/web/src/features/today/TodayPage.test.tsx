import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { TodayPage } from "./TodayPage";

type Exercise = components["schemas"]["Exercise"];
type Today = components["schemas"]["TodayV2"];
type Split = components["schemas"]["Split"];

const press: Exercise = {
  id: "press",
  scope: "global",
  can_edit: false,
  slug: "incline-press",
  name: "Incline Press",
  aliases: [],
  variation_group: "incline_press",
  movement_pattern: "horizontal_push",
  equipment: "dumbbell",
  measurement_type: "load_reps",
  compound: true,
  unilateral: false,
  default_rep_min: 8,
  default_rep_max: 12,
  default_rest_seconds: 120,
  automatic_progression_enabled: true,
  muscle_targets: [],
};

const row: Exercise = { ...press, id: "row", slug: "row", name: "Cable Row", variation_group: "row", movement_pattern: "horizontal_pull", equipment: "cable" };
const curl: Exercise = { ...press, id: "curl", slug: "curl", name: "Cable Curl", variation_group: "curl", movement_pattern: "elbow_flexion", equipment: "cable", compound: false };

const day = {
  id: "upper-a",
  name: "Upper A",
  day_type: "upper",
  sequence: 1,
  is_optional: false,
  items: [],
};

const split: Split = {
  id: "split-1",
  name: "Upper / Lower",
  slug: "upper-lower",
  is_active: true,
  days: [day, { ...day, id: "lower-a", name: "Lower A", sequence: 2 }],
};

const today: Today = {
  local_date: "2026-07-15",
  user: { id: "user-1", email: "member@example.com", display_name: "Alex", role: "member", account_status: "active", timezone: "America/Toronto", preferred_units: "metric" },
  planned_day: day,
  effective_day: day,
  override: null,
  schedule_version: 7,
  exercise_plan: [
    { id: "plan-press", source_template_item_id: "template-press", exercise: press, sequence: 1, item_type: "main", planned_sets: 3, rep_min: 8, rep_max: 12, optional: false },
    { id: "plan-row", source_template_item_id: "template-row", exercise: row, sequence: 2, item_type: "main", planned_sets: 3, rep_min: 8, rep_max: 12, optional: false },
  ],
  active_session: null,
  muscle_targets: [{ slug: "upper_chest", display_name: "Upper Chest", role: "primary", intensity: 1, svg_region_ids: ["chest_upper"] }],
  water: { local_date: "2026-07-15", total_ml: 0, goal_ml: 2800, progress_ratio: 0, entries: [] },
  latest_achievements: [],
  avatar: { base_presentation: "male", skin_tone: "medium", hairstyle: "short_coils", hair_color: "black", outfit_style: "training_tee", outfit_palette: "violet", accessory: "none", background: "none", aura_style: "standard", aura_enabled: true },
  streak: { current_count: 4, longest_count: 9, tier: "active", last_qualified_local_date: "2026-07-14", next_milestone: 7 },
};

function renderPage(todayResponse: Today = today) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
    if (path === "/today") return { data: todayResponse, response: new Response() } as never;
    if (path === "/settings") return { data: { week_starts_on: 1, default_water_goal_ml: 2800, water_quick_add_ml: [250, 500], reduced_motion_override: null, visibility: {} }, response: new Response() } as never;
    if (path === "/splits") return { data: [split], response: new Response() } as never;
    return { data: [press, row, curl], response: new Response() } as never;
  });
  return { queryClient, ...render(<QueryClientProvider client={queryClient}><TodayPage /></QueryClientProvider>) };
}

afterEach(() => vi.restoreAllMocks());

describe("TodayPage", () => {
  it("renders the private v2 plan, avatar targets, and hydration", async () => {
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent("Waking up your training data");
    expect(await screen.findByRole("heading", { name: "Ready for Upper A" })).toBeInTheDocument();
    expect(screen.getByText("Incline Press")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent("Upper Chest");
    expect(screen.getByRole("heading", { name: "0 mL" })).toBeInTheDocument();
  });

  it("skips today with explicit advance or keep behavior", async () => {
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({ data: { ...today, schedule_version: 8 }, response: new Response() } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Skip today" }));
    fireEvent.click(screen.getByLabelText("Keep this workout next"));
    fireEvent.click(screen.getByRole("button", { name: "Confirm skip" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/today/skip", expect.objectContaining({
      body: { local_date: "2026-07-15", schedule_effect: "keep", expected_version: 7 },
      params: { header: { "Idempotency-Key": expect.any(String) } },
    })));
    expect(await screen.findByRole("status")).toHaveTextContent("next workout stays in place");
  });

  it.each([
    ["One time only", "one_time", undefined],
    ["Continue from here", "continue_from_here", undefined],
    ["Swap forward", "swap_forward", "2026-07-18"],
  ] as const)("changes workout with %s schedule behavior", async (label, expectedEffect, swapDate) => {
    const put = vi.spyOn(apiClient, "PUT").mockResolvedValue({ data: { ...today, schedule_version: 8 }, response: new Response() } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Change workout" }));
    fireEvent.change(screen.getByLabelText("Replacement workout"), { target: { value: "lower-a" } });
    fireEvent.click(screen.getByLabelText(label));
    if (swapDate) fireEvent.change(screen.getByLabelText("Swap target date"), { target: { value: swapDate } });
    fireEvent.click(screen.getByRole("button", { name: "Apply workout change" }));
    await waitFor(() => expect(put).toHaveBeenCalled());
    const body = put.mock.calls[0]?.[1]?.body;
    expect(body).toEqual(expect.objectContaining({ effective_split_day_id: "lower-a", expected_version: 7, schedule_effect: expectedEffect }));
    expect(body).toEqual(expect.objectContaining(expectedEffect === "swap_forward" ? { action: "swap", swap_target_local_date: swapDate } : { action: "replace" }));
  });

  it("adds, removes, reorders, and swaps before an explicit today-only save", async () => {
    const put = vi.spyOn(apiClient, "PUT").mockResolvedValue({ data: today, response: new Response() } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Edit exercises" }));
    fireEvent.change(screen.getByLabelText("Exercise to add"), { target: { value: "curl" } });
    fireEvent.click(screen.getByRole("button", { name: "Add exercise" }));
    fireEvent.click(screen.getByRole("button", { name: "Move Cable Curl up" }));
    fireEvent.change(screen.getByLabelText("Swap Incline Press"), { target: { value: "curl" } });
    fireEvent.click(screen.getByRole("button", { name: "Remove Cable Row" }));
    fireEvent.click(screen.getByRole("button", { name: "Save for today only" }));
    await waitFor(() => expect(put).toHaveBeenCalledWith("/today/exercises", expect.objectContaining({
      body: expect.objectContaining({ scope: "today_only", expected_version: 7, items: expect.any(Array) }),
    })));
    const items = (put.mock.calls[0]?.[1]?.body as components["schemas"]["TodayExercisePlanUpdate"]).items;
    expect(items).toHaveLength(2);
    expect(items.map((item) => item.exercise_id)).toEqual(["curl", "curl"]);
    expect(items.map((item) => item.sequence)).toEqual([1, 2]);
  });

  it("can save an exercise edit back to the split", async () => {
    const put = vi.spyOn(apiClient, "PUT").mockResolvedValue({ data: today, response: new Response() } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Edit exercises" }));
    fireEvent.click(screen.getByLabelText("Save these changes to the split too"));
    fireEvent.click(screen.getByRole("button", { name: "Save today and split" }));
    await waitFor(() => expect(put).toHaveBeenCalledWith("/today/exercises", expect.objectContaining({ body: expect.objectContaining({ scope: "save_to_split", source_split_day_id: "upper-a" }) })));
  });

  it("announces version conflicts and refetches authoritative state", async () => {
    vi.spyOn(apiClient, "POST").mockResolvedValue({ error: { error: { code: "conflict", message: "stale", current_version: 8 } }, response: new Response(null, { status: 409 }) } as never);
    const { queryClient } = renderPage();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    fireEvent.click(await screen.findByRole("button", { name: "Skip today" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm skip" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("schedule changed elsewhere");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["today"] });
  });
});
