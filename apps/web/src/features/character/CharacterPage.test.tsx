import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { CharacterPage } from "./CharacterPage";

type AvatarSettings = components["schemas"]["AvatarSettings"];
type Profile = components["schemas"]["Profile"];
type Settings = components["schemas"]["Settings"];
type Streak = components["schemas"]["StreakSummary"];
type Today = components["schemas"]["TodayV2"];

const avatar: AvatarSettings = {
  base_presentation: "male",
  skin_tone: "deep",
  hairstyle: "short_coils",
  hair_color: "black",
  outfit_style: "tank_and_shorts",
  outfit_palette: "violet",
  accessory: "none",
  background: "gradient",
  aura_style: "rings",
  aura_enabled: true,
};

const profile: Profile = {
  id: "profile-1",
  display_name: "Brandan Burgess",
  height_cm: 179,
  body_weight_kg: 79.38,
  preferred_units: "imperial",
  timezone: "America/Toronto",
};

const settings = {
  week_starts_on: 1,
  default_water_goal_ml: 3000,
  water_quick_add_ml: [250, 500],
  reduced_motion_override: true,
  visibility: {},
} as Settings;

const streak: Streak = {
  current_count: 8,
  longest_count: 14,
  tier: "active",
  last_qualified_local_date: "2026-07-14",
  next_milestone: 14,
};

const today = {
  local_date: "2026-07-15",
  user: {
    id: "user-1",
    email: "member@example.com",
    display_name: "Brandan Burgess",
    role: "member",
    account_status: "active",
    timezone: "America/Toronto",
    preferred_units: "imperial",
  },
  planned_day: null,
  effective_day: { id: "upper-a", name: "Upper A", day_type: "upper", sequence: 0, is_optional: false, items: [] },
  override: null,
  schedule_version: 3,
  exercise_plan: [],
  active_session: null,
  muscle_targets: [
    { slug: "upper-chest", display_name: "Upper Chest", role: "primary", intensity: 1, svg_region_ids: ["chest_upper"] },
  ],
  water: { local_date: "2026-07-15", total_ml: 0, goal_ml: 3000, progress_ratio: 0, entries: [] },
  latest_achievements: [],
  avatar,
  streak,
} as Today;

function mockCharacterApi() {
  return vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
    const data = path === "/me/profile"
      ? profile
      : path === "/settings"
        ? settings
        : path === "/me/avatar"
          ? avatar
          : path === "/me/streak"
            ? streak
            : today;
    return { data, response: new Response() } as never;
  });
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CharacterPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("CharacterPage", () => {
  it("keeps the overview, accessible muscle text, aura, and selectable front/back views", async () => {
    mockCharacterApi();
    const { container } = renderPage();

    expect(await screen.findByRole("heading", { name: "Brandan Burgess" })).toBeInTheDocument();
    expect(screen.getByText("5 ft 10 in")).toBeInTheDocument();
    expect(screen.getByText("175 lb")).toBeInTheDocument();
    expect(screen.getByText("Upper A")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent("Upper Chest");
    expect(container.querySelector('[data-aura-tier="active"]')).not.toBeNull();
    expect(container.querySelector('[data-reduced-motion="true"]')).not.toBeNull();
    expect(container.querySelector('[data-avatar-view="front"]')).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("button", { name: "Back" })).toHaveAttribute("aria-pressed", "true");
    expect(container.querySelector('[data-avatar-view="back"]')).not.toBeNull();
  });

  it("saves member profile measurements through the private profile endpoint", async () => {
    mockCharacterApi();
    const patch = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: { ...profile, height_cm: 180, body_weight_kg: 80 },
      response: new Response(),
    } as never);
    renderPage();

    fireEvent.change(await screen.findByRole("spinbutton", { name: "Height in centimetres" }), { target: { value: "180" } });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Body weight in kilograms" }), { target: { value: "80" } });
    fireEvent.click(screen.getByRole("button", { name: "Save measurements" }));

    await waitFor(() => expect(patch).toHaveBeenCalledWith("/me/profile", {
      body: { height_cm: 180, body_weight_kg: 80 },
    }));
    expect(await screen.findByText("Profile measurements saved.")).toHaveAttribute("role", "status");
  });

  it("loads Appearance, previews both bases, and persists controlled settings through /me/avatar", async () => {
    mockCharacterApi();
    const patch = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: { ...avatar, base_presentation: "female", aura_enabled: false },
      response: new Response(),
    } as never);
    const { container } = renderPage();

    const overviewTab = screen.getByRole("tab", { name: "Overview" });
    overviewTab.focus();
    fireEvent.keyDown(overviewTab, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Appearance" })).toHaveFocus();
    expect(await screen.findByRole("heading", { name: "Appearance" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Female" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Show streak aura/ }));
    expect(container.querySelector('[data-base-presentation="female"]')).not.toBeNull();
    expect(container.querySelector("[data-aura-tier]")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Save appearance" }));
    await waitFor(() => expect(patch).toHaveBeenCalledWith("/me/avatar", {
      body: { ...avatar, base_presentation: "female", aura_enabled: false },
    }));
    expect(await screen.findByText("Appearance saved.")).toHaveAttribute("role", "status");
  });
});
