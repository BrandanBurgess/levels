import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { SettingsPage } from "./SettingsPage";

const profile = {
  id: "profile-1",
  display_name: "Brandan Burgess",
  height_cm: 179,
  body_weight_kg: 79.38,
  preferred_units: "imperial" as const,
  timezone: "America/Toronto",
  avatar_variant: "brandan-original-v1",
};

const settings = {
  active_split_id: "split-1",
  week_starts_on: 1,
  default_water_goal_ml: 2800,
  water_quick_add_ml: [250, 500, 750],
  default_target_rir: 2,
  default_load_increment_kg: 2.5,
  reduced_motion_override: null,
  visibility: {
    show_height: true,
    show_body_weight: false,
    show_water: false,
    show_session_summaries: true,
    show_set_details: false,
    show_public_notes: true,
    show_progress_charts: true,
    show_personal_records: true,
    show_readiness: false,
  },
};

const splits = [
  {
    id: "split-1",
    name: "Upper / Lower",
    slug: "upper_lower",
    is_active: true,
    days: [],
  },
];

function renderPage(isAuthenticated: boolean) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const logout = vi.fn();
  const auth: AuthState = {
    ...(isAuthenticated ? { admin: { displayName: "Brandan Burgess" } } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout,
  };
  return {
    logout,
    ...render(
      <MemoryRouter>
        <AuthContext.Provider value={auth}>
          <QueryClientProvider client={queryClient}>
            <SettingsPage />
          </QueryClientProvider>
        </AuthContext.Provider>
      </MemoryRouter>,
    ),
  };
}

function mockSettingsReads() {
  return vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
    if (path === "/profile") return { data: profile, response: new Response() };
    if (path === "/settings") return { data: settings, response: new Response() };
    return { data: splits, response: new Response() };
  });
}

afterEach(() => {
  document.documentElement.removeAttribute("data-reduced-motion");
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("SettingsPage", () => {
  it("keeps owner settings behind sign-in", () => {
    const get = vi.spyOn(apiClient, "GET");
    renderPage(false);

    expect(screen.getByRole("heading", { name: "Owner sign-in required" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in to continue" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(get).not.toHaveBeenCalled();
  });

  it("saves profile, training, hydration, privacy, and motion settings", async () => {
    mockSettingsReads();
    const patch = vi.spyOn(apiClient, "PATCH").mockImplementation(async (path) => {
      if (path === "/profile") {
        return { data: { ...profile, display_name: "Brandan B." }, response: new Response() };
      }
      return {
        data: { ...settings, default_water_goal_ml: 3200, reduced_motion_override: true },
        response: new Response(),
      };
    });
    renderPage(true);

    fireEvent.change(await screen.findByRole("textbox", { name: "Display name" }), {
      target: { value: "Brandan B." },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Daily water goal (mL)" }), {
      target: { value: "3200" },
    });
    fireEvent.change(
      screen.getByRole("textbox", { name: "Quick-add amounts (mL, comma-separated)" }),
      { target: { value: "300, 600" } },
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /Hydration/ }));
    fireEvent.change(screen.getByRole("combobox", { name: "Animation" }), {
      target: { value: "reduce" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(patch).toHaveBeenCalledTimes(2));
    expect(patch).toHaveBeenCalledWith(
      "/profile",
      expect.objectContaining({ body: expect.objectContaining({ display_name: "Brandan B." }) }),
    );
    expect(patch).toHaveBeenCalledWith(
      "/settings",
      expect.objectContaining({
        body: expect.objectContaining({
          week_starts_on: 1,
          default_water_goal_ml: 3200,
          water_quick_add_ml: [300, 600],
          reduced_motion_override: true,
          visibility: expect.objectContaining({ show_water: true }),
        }),
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Settings saved");
    expect(document.documentElement).toHaveAttribute("data-reduced-motion", "true");
  });

  it("signs the owner out from account tools", async () => {
    mockSettingsReads();
    const { logout } = renderPage(true);

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(logout).toHaveBeenCalledOnce();
  });
});
