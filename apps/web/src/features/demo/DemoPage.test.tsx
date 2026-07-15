import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { DemoPage } from "./DemoPage";

vi.mock("../../api/client", () => ({ apiClient: { GET: vi.fn() } }));

type DemoBootstrap = components["schemas"]["DemoBootstrap"];

const demo = {
  mode: "demo",
  profile: { display_name: "Maya Demo", preferred_units: "metric", timezone: "America/Toronto" },
  avatar: { base_presentation: "female", skin_tone: "medium", hairstyle: "braids", hair_color: "black", outfit_style: "training_tee", outfit_palette: "violet", accessory: "none", background: "gradient", aura_style: "standard", aura_enabled: true },
  streak: { current_count: 7, longest_count: 10, tier: "active", last_qualified_local_date: "2026-07-14", next_milestone: 14 },
  today: {
    local_date: "2026-07-15",
    profile: { display_name: "Maya Demo", preferred_units: "metric", timezone: "America/Toronto" },
    effective_day: { id: "day-1", name: "Upper A", day_type: "training", sequence: 1, is_optional: false, items: [] },
    exercise_plan: [{ id: "plan-1", exercise: { id: "exercise-1", name: "Bench press" }, sequence: 0, item_type: "main", planned_sets: 3, optional: false }],
    muscle_targets: [],
    avatar: { base_presentation: "female", skin_tone: "medium", hairstyle: "braids", hair_color: "black", outfit_style: "training_tee", outfit_palette: "violet", accessory: "none", background: "gradient", aura_style: "standard", aura_enabled: true },
    streak: { current_count: 7, longest_count: 10, tier: "active", last_qualified_local_date: "2026-07-14", next_milestone: 14 },
  },
  splits: [],
  exercises: [],
  journal_samples: [],
  progress: { completed_sessions: 12, current_records: [] },
} as unknown as DemoBootstrap;

function renderDemo() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={["/demo"]}><DemoPage /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => vi.mocked(apiClient.GET).mockResolvedValue({ data: demo } as never));

describe("DemoPage", () => {
  it("loads the anonymous bootstrap and keeps persistent actions read-only", async () => {
    renderDemo();
    expect(await screen.findByRole("heading", { name: "Today with Maya Demo" })).toBeInTheDocument();
    expect(apiClient.GET).toHaveBeenCalledWith("/demo/bootstrap");
    expect(screen.getByText("Demo — changes are not saved")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start workout" }));
    expect(screen.getByText("Create an account to save changes.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Create account" }).at(-1)).toHaveAttribute("href", "/register");
  });
});
