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
const sessions = [{ id: "session-1", version: 1, split_day_id: "upper-a", session_date_local: "2026-07-10", started_at: "2026-07-10T12:00:00Z", completed_at: "2026-07-10T13:00:00Z", status: "completed" as const, title: "Upper A", perceived_effort: 7, exercises: [{ id: "item", exercise_id: "press", display_name: "Incline Press", variation_group: "press", sequence: 1, planned_sets: 3, item_type: "main" as const, optional: false, sets: [] }] }];

function renderPage(isAuthenticated = false, records = { current, history }, units: "metric" | "imperial" = "metric") {
  vi.spyOn(apiClient, "GET")
    .mockResolvedValueOnce({ data: [...records.current], response: new Response() } as never)
    .mockResolvedValueOnce({ data: [...records.history], response: new Response() } as never)
    .mockResolvedValueOnce({ data: exercises, response: new Response() } as never)
    .mockResolvedValueOnce({ data: sessions, response: new Response() } as never);
  const auth: AuthState = {
    ...(isAuthenticated ? {
      admin: { displayName: "Brandan" },
      user: { id: "user-1", email: "member@example.com", display_name: "Brandan", role: "member" as const, account_status: "active" as const, timezone: "America/Toronto", preferred_units: units },
    } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(),
  };
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
    expect(apiClient.GET).toHaveBeenCalledWith("/sessions", { params: { query: {} } });
  });

  it("converts weight-derived records using the owner's persisted imperial preference", async () => {
    const maxLoad: RecordItem = { ...currentRecord, id: "max-load", record_type: "max_load", unit: "kg reps", value_numeric: 100 };
    renderPage(true, { current: [currentRecord, maxLoad], history }, "imperial");

    expect(await screen.findAllByText("176.37 lb estimated")).not.toHaveLength(0);
    expect(screen.getByText("220.46 lb reps")).toBeInTheDocument();
    expect(screen.getAllByText(/moved from 165.35 lb estimated to 176.37 lb estimated/)).not.toHaveLength(0);
  });

  it("explains a privacy-safe empty records state", async () => {
    renderPage(false, { current: [], history: [] });
    expect(await screen.findByRole("heading", { name: "No visible records" })).toBeInTheDocument();
  });

  it("offers authenticated JSON export and keeps it out of the public page", async () => {
    const { unmount } = renderPage();
    await screen.findByRole("heading", { name: "Personal records" });
    expect(screen.queryByRole("heading", { name: "Export your data" })).not.toBeInTheDocument();
    unmount();

    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderPage(true);
    await screen.findByRole("heading", { name: "Export your data" });
    vi.mocked(apiClient.GET).mockResolvedValueOnce({ data: { tables: {} }, response: new Response() } as never);
    fireEvent.click(screen.getByRole("button", { name: "Download JSON" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Export ready.");
    expect(createObjectURL).toHaveBeenCalled();
    expect(apiClient.GET).toHaveBeenLastCalledWith("/export", { params: { query: { format: "json" } } });
  });
});
