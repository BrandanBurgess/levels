import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { ProgressPage } from "./ProgressPage";

type RecordItem = components["schemas"]["PersonalRecord"];

const currentRecord: RecordItem = { id: "current-e1rm", exercise_id: "press", exercise_name: "Incline Press", record_type: "estimated_1rm", value_numeric: 80, unit: "kg estimated", reps_context: 8, achieved_at: "2026-07-10T12:00:00Z" };
const current: RecordItem[] = [currentRecord];
const history: RecordItem[] = [
  { ...currentRecord, id: "old-e1rm", value_numeric: 75, achieved_at: "2026-07-01T12:00:00Z" },
  currentRecord,
];
const exercises = [{ id: "press", slug: "incline_press", name: "Incline Press", aliases: [], variation_group: "incline_press", movement_pattern: "horizontal_push", equipment: "barbell", measurement_type: "load_reps" as const, compound: true, unilateral: false, automatic_progression_enabled: true, muscle_targets: [{ slug: "upper_chest", display_name: "Upper Chest", role: "primary" as const, intensity: 1, svg_region_ids: ["chest_upper"] }] }];
const sessions = [{ id: "session-1", split_day_id: "upper-a", session_date_local: "2026-07-10", started_at: "2026-07-10T12:00:00Z", completed_at: "2026-07-10T13:00:00Z", status: "completed" as const, title: "Upper A", public_visibility: "full" as const, perceived_effort: 7, exercises: [{ id: "item", exercise_id: "press", display_name: "Incline Press", sequence: 1, sets: [] }] }];

function renderPage(isAuthenticated = false, records = { current, history }) {
  vi.spyOn(apiClient, "GET")
    .mockResolvedValueOnce({ data: [...records.current], response: new Response() } as never)
    .mockResolvedValueOnce({ data: [...records.history], response: new Response() } as never)
    .mockResolvedValueOnce({ data: exercises, response: new Response() } as never)
    .mockResolvedValueOnce({ data: sessions, response: new Response() } as never);
  const auth: AuthState = { ...(isAuthenticated ? { admin: { displayName: "Brandan" } } : {}), isAuthenticated, isSubmitting: false, login: vi.fn(async () => false), logout: vi.fn() };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<AuthContext.Provider value={auth}><QueryClientProvider client={client}><ProgressPage /></QueryClientProvider></AuthContext.Provider>);
}

afterEach(() => vi.restoreAllMocks());

describe("ProgressPage", () => {
  it("shows records, an explicitly estimated accessible trend, and neutral consistency", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Personal records" })).toBeInTheDocument();
    expect(screen.getByText("Estimate, not a measured max")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Estimated 1RM trend" })).toBeInTheDocument();
    expect(screen.getAllByText(/moved from 75 kg estimated to 80 kg estimated/)).not.toHaveLength(0);
    expect(screen.getByRole("list", { name: "28-day training calendar" })).toHaveTextContent("Open day");
    expect(screen.queryByText(/missed|failed/i)).not.toBeInTheDocument();
  });

  it("filters records by exercise and muscle and requests private history only for owner", async () => {
    renderPage(true);
    await screen.findByRole("heading", { name: "Personal records" });
    fireEvent.change(screen.getByLabelText("Exercise"), { target: { value: "press" } });
    fireEvent.change(screen.getByLabelText("Muscle"), { target: { value: "upper_chest" } });
    expect(screen.getAllByText("Incline Press")).not.toHaveLength(0);
    expect(apiClient.GET).toHaveBeenCalledWith("/sessions", { params: { query: { public_only: false } } });
  });

  it("explains a privacy-safe empty records state", async () => {
    renderPage(false, { current: [], history: [] });
    expect(await screen.findByRole("heading", { name: "No visible records" })).toBeInTheDocument();
  });
});
