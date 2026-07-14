import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { CharacterPage } from "./CharacterPage";

const profile = {
  display_name: "Brandan Burgess",
  height_cm: 179,
  body_weight_kg: 79.38,
  preferred_units: "imperial" as const,
  timezone: "America/Toronto",
  avatar_variant: "default",
};

const dashboard = {
  date: "2026-07-13",
  profile,
  scheduled_day: null,
  active_session: null,
  muscle_targets: [
    {
      slug: "upper-chest",
      display_name: "Upper Chest",
      role: "primary" as const,
      intensity: 1,
      svg_region_ids: ["chest_upper"],
    },
  ],
  water: null,
  latest_achievements: [],
};

function renderPage(isAuthenticated = false) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth: AuthState = {
    ...(isAuthenticated ? { admin: { displayName: "Brandan Burgess" } } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(),
  };
  return render(
    <AuthContext.Provider value={auth}>
      <QueryClientProvider client={queryClient}>
        <CharacterPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("CharacterPage", () => {
  it("shows public measurements, muscle text, and selectable front/back views", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: dashboard, response: new Response() });

    const { container } = renderPage();

    expect(await screen.findByRole("heading", { name: "Brandan Burgess" })).toBeInTheDocument();
    expect(screen.getByText("5 ft 10 in")).toBeInTheDocument();
    expect(screen.getByText("175 lb")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent(
      "Upper Chest",
    );
    expect(container.querySelector('[data-avatar-view="front"]')).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("button", { name: "Back" })).toHaveAttribute("aria-pressed", "true");
    expect(container.querySelector('[data-avatar-view="back"]')).not.toBeNull();
  });

  it("lets the authenticated owner save direct measurement entries", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: dashboard, response: new Response() });
    const updateProfile = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: { id: "profile", ...profile, height_cm: 180, body_weight_kg: 80 },
      response: new Response(),
    });

    renderPage(true);

    fireEvent.change(await screen.findByRole("spinbutton", { name: "Height in centimetres" }), {
      target: { value: "180" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Body weight in kilograms" }), {
      target: { value: "80" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save measurements" }));

    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith("/profile", {
        body: { height_cm: 180, body_weight_kg: 80 },
      }),
    );
    expect(await screen.findByText("Profile measurements saved.")).toHaveAttribute("role", "status");
  });
});
