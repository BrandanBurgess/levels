import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { SplitsPage } from "./SplitsPage";

function exercise(id: string, name: string) {
  return { id, slug: id, name, aliases: [], variation_group: id, movement_pattern: "push", equipment: "bodyweight", measurement_type: "bodyweight_reps" as const, compound: true, unilateral: false, automatic_progression_enabled: true, muscle_targets: [] };
}

const pushUp = exercise("push_up", "Push-Up");
const press = exercise("incline_press", "Incline Press");
const split = {
  id: "split-1", name: "Upper Lower", slug: "upper-lower", description: "Four focused days", is_active: true,
  days: [
    { id: "day-1", name: "Upper A", day_type: "upper", sequence: 1, is_optional: false, items: [{ id: "item-1", exercise: pushUp, sequence: 1, item_type: "main" as const, sets: 3, optional: false, alternatives: [press] }] },
    { id: "day-2", name: "Lower A", day_type: "lower", sequence: 2, is_optional: false, items: [] },
  ],
};

function renderPage(isAuthenticated = false) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth: AuthState = { ...(isAuthenticated ? { admin: { displayName: "Brandan" } } : {}), isAuthenticated, isSubmitting: false, login: vi.fn(async () => false), logout: vi.fn() };
  return render(<AuthContext.Provider value={auth}><QueryClientProvider client={queryClient}><SplitsPage /></QueryClientProvider></AuthContext.Provider>);
}

afterEach(() => vi.restoreAllMocks());

describe("SplitsPage", () => {
  it("shows ordered public days and alternatives before selection", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: [split], response: new Response() });
    renderPage();

    expect(await screen.findByRole("heading", { name: "Upper Lower" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Upper A" })).toBeInTheDocument();
    expect(screen.getByText("Alternatives: Incline Press")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Move Upper A down" })).not.toBeInTheDocument();
  });

  it("provides keyboard-safe reorder and persists stable IDs", async () => {
    vi.spyOn(apiClient, "GET").mockImplementation(async (path) => ({ data: path === "/splits" ? [split] : [pushUp, press], response: new Response() }));
    const patchSplit = vi.spyOn(apiClient, "PATCH").mockResolvedValue({ data: split, response: new Response() });
    renderPage(true);

    fireEvent.click(await screen.findByRole("button", { name: "Move Lower A up" }));
    fireEvent.click(screen.getByRole("button", { name: "Save order" }));

    await waitFor(() => expect(patchSplit).toHaveBeenCalled());
    expect(patchSplit).toHaveBeenCalledWith(
      "/splits/{split_id}",
      expect.objectContaining({
        body: expect.objectContaining({
          days: [expect.objectContaining({ id: "day-2", sequence: 1 }), expect.objectContaining({ id: "day-1", sequence: 2 })],
        }),
      }),
    );
    expect(await screen.findByText("Split changes saved.")).toHaveAttribute("role", "status");
  });

  it("lets the owner create a new split", async () => {
    vi.spyOn(apiClient, "GET").mockImplementation(async (path) => ({ data: path === "/splits" ? [split] : [pushUp], response: new Response() }));
    const postSplit = vi.spyOn(apiClient, "POST").mockResolvedValue({ data: { ...split, id: "new-split", name: "My Plan", slug: "my-plan", days: [] }, response: new Response() });
    renderPage(true);

    fireEvent.change(await screen.findByRole("textbox", { name: "New split" }), { target: { value: "My Plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(postSplit).toHaveBeenCalledWith("/splits", { body: { name: "My Plan", slug: "my-plan", days: [] } }));
  });
});
