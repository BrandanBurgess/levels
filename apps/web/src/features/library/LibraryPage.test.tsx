import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { LibraryPage } from "./LibraryPage";

const target = {
  slug: "upper_chest",
  display_name: "Upper Chest",
  role: "primary" as const,
  intensity: 1,
  svg_region_ids: ["chest_upper"],
};

const exercises = [
  {
    id: "incline_barbell_bench_press",
    slug: "incline_barbell_bench_press",
    name: "Incline Barbell Bench Press",
    aliases: ["incline bench"],
    variation_group: "incline_press",
    movement_pattern: "horizontal_push",
    equipment: "barbell",
    measurement_type: "load_reps" as const,
    compound: true,
    unilateral: false,
    automatic_progression_enabled: true,
    muscle_targets: [target],
  },
  {
    id: "incline_dumbbell_press",
    slug: "incline_dumbbell_press",
    name: "Incline Dumbbell Press",
    aliases: ["incline db press"],
    variation_group: "incline_press",
    movement_pattern: "horizontal_push",
    equipment: "dumbbell",
    measurement_type: "load_reps" as const,
    compound: true,
    unilateral: false,
    automatic_progression_enabled: true,
    muscle_targets: [target],
  },
];

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <LibraryPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("LibraryPage", () => {
  it("groups variations and shows avatar-backed exercise detail", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: exercises, response: new Response() });

    const { container } = renderPage();

    expect(await screen.findByRole("heading", { name: "incline press" })).toBeInTheDocument();
    expect(screen.getByText("2 movements · 1 variation groups")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Incline Barbell Bench Press" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent(
      "Upper Chest",
    );
    expect(container.querySelector('[data-muscle-id="chest_upper"]')).toHaveClass(
      "avatar-region--primary",
    );

    fireEvent.click(screen.getByRole("button", { name: /Incline Dumbbell Press/ }));
    expect(screen.getByRole("heading", { name: "Incline Dumbbell Press" })).toBeInTheDocument();
    expect(screen.getByText("Incline Barbell Bench Press", { selector: "li" })).toBeInTheDocument();
  });

  it("sends search and filter values through the generated API client", async () => {
    const getExercises = vi
      .spyOn(apiClient, "GET")
      .mockResolvedValue({ data: exercises, response: new Response() });
    renderPage();
    await screen.findByText("2 movements · 1 variation groups");

    fireEvent.change(screen.getByRole("searchbox", { name: "Search names and aliases" }), {
      target: { value: "incline bench" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Primary muscle" }), {
      target: { value: "upper_chest" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Laterality" }), {
      target: { value: "bilateral" },
    });

    await waitFor(() =>
      expect(getExercises).toHaveBeenLastCalledWith("/exercises", {
        params: {
          query: { q: "incline bench", primary_muscle: "upper_chest", unilateral: false },
        },
      }),
    );
  });

  it("renders a useful empty state", async () => {
    vi.spyOn(apiClient, "GET").mockResolvedValue({ data: [], response: new Response() });
    renderPage();
    expect(await screen.findByRole("heading", { name: "No movements match" })).toBeInTheDocument();
  });
});
