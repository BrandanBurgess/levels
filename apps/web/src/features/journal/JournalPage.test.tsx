import type { components } from "@levels/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import { AuthContext, type AuthState } from "../../auth/context";
import { JournalPage } from "./JournalPage";

type WorkoutSession = components["schemas"]["WorkoutSession"];

const exercise = {
  id: "incline_press",
  slug: "incline-press",
  name: "Incline Press",
  aliases: [],
  variation_group: "incline_press",
  movement_pattern: "horizontal_push",
  equipment: "barbell",
  measurement_type: "load_reps" as const,
  compound: true,
  unilateral: false,
  automatic_progression_enabled: true,
  muscle_targets: [],
};

const loggedSet = {
  id: "set-1",
  sequence: 1,
  set_type: "working" as const,
  load_kg: 60,
  reps: 8,
  rir: 2,
  form_quality: 4,
  pain_flag: false,
  completed_at: "2026-07-13T12:00:00Z",
};

const activeSession: WorkoutSession = {
  id: "session-1",
  session_date_local: "2026-07-13",
  started_at: "2026-07-13T11:00:00Z",
  status: "in_progress" as const,
  title: "Upper A",
  public_visibility: "private" as const,
  exercises: [
    {
      id: "session-exercise-1",
      exercise_id: exercise.id,
      display_name: exercise.name,
      variation_group: exercise.variation_group,
      sequence: 1,
      rep_min: 6,
      rep_max: 10,
      sets: [loggedSet],
    },
  ],
};

const dashboard = {
  date: "2026-07-13",
  profile: {
    display_name: "Brandan",
    preferred_units: "metric" as const,
    timezone: "America/Toronto",
    avatar_variant: "default",
  },
  scheduled_day: {
    id: "day-1",
    name: "Upper A",
    day_type: "upper",
    sequence: 1,
    is_optional: false,
    items: [],
  },
  muscle_targets: [],
  latest_achievements: [],
};

function renderPage(isAuthenticated: boolean, sessions: WorkoutSession[] = [activeSession]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth: AuthState = {
    ...(isAuthenticated ? { admin: { displayName: "Brandan" } } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(),
  };
  vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
    if (path === "/sessions") return { data: sessions, response: new Response() };
    if (path === "/exercises") return { data: [exercise], response: new Response() };
    return { data: dashboard, response: new Response() };
  });
  return render(
    <AuthContext.Provider value={auth}>
      <QueryClientProvider client={queryClient}>
        <JournalPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("JournalPage", () => {
  it("shows a privacy-safe completed public journal", async () => {
    const completed = {
      ...activeSession,
      status: "completed" as const,
      public_visibility: "full" as const,
    };
    renderPage(false, [completed]);

    expect(await screen.findByRole("heading", { name: "Upper A" })).toBeInTheDocument();
    expect(screen.getByText("60 kg × 8")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Log set" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Private notes")).not.toBeInTheDocument();
  });

  it("opens today's scheduled template for the owner", async () => {
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: activeSession,
      response: new Response(),
    });
    renderPage(true, []);

    fireEvent.click(await screen.findByRole("button", { name: "Start Upper A" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        "/sessions",
        expect.objectContaining({ body: { split_day_id: "day-1" } }),
      ),
    );
  });

  it("provides mobile numeric inputs, fast controls, and set duplication", async () => {
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: { set: loggedSet, new_achievements: [], affected_records: [] },
      response: new Response(),
    });
    renderPage(true);

    const weight = await screen.findByRole("spinbutton", { name: "Weight (kg)" });
    const reps = screen.getByRole("spinbutton", { name: "Reps" });
    expect(weight).toHaveAttribute("inputmode", "decimal");
    expect(reps).toHaveAttribute("inputmode", "numeric");

    fireEvent.click(screen.getByRole("button", { name: "Increase Incline Press weight" }));
    fireEvent.click(screen.getByRole("button", { name: "Increase Incline Press reps" }));
    fireEvent.click(screen.getByRole("button", { name: "Log set" }));

    await waitFor(() => expect(post).toHaveBeenCalled());
    expect(post).toHaveBeenCalledWith(
      "/sessions/{session_id}/sets",
      expect.objectContaining({
        params: expect.objectContaining({ path: { session_id: "session-1" } }),
        body: expect.objectContaining({
          session_exercise_id: "session-exercise-1",
          load_kg: 2.5,
          reps: 1,
        }),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Duplicate previous" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ body: expect.objectContaining({ load_kg: 60, reps: 8 }) }),
    );
  });

  it("exposes session-only substitution and completion controls", async () => {
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: activeSession.exercises[0],
      response: new Response(),
    });
    const patch = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: { ...activeSession, status: "completed" as const },
      response: new Response(),
    });
    renderPage(true);

    expect(await screen.findByRole("button", { name: "Substitute" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Complete workout" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    expect(patch).toHaveBeenCalledWith(
      "/sessions/{session_id}",
      expect.objectContaining({ body: expect.objectContaining({ status: "completed" }) }),
    );
    expect(post).not.toHaveBeenCalled();
  });

  it("restores the latest local set and notes draft after a refresh", async () => {
    const first = renderPage(true);

    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (kg)" }), {
      target: { value: "82.5" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Private notes" }), {
      target: { value: "Keep shoulder packed" },
    });
    first.unmount();
    renderPage(true);

    expect(await screen.findByRole("spinbutton", { name: "Weight (kg)" })).toHaveValue(82.5);
    expect(screen.getByRole("textbox", { name: "Private notes" })).toHaveValue(
      "Keep shoulder packed",
    );
  });

  it("keeps a failed write local and retries explicitly with the same key", async () => {
    const post = vi
      .spyOn(apiClient, "POST")
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce({
        data: { set: loggedSet, new_achievements: [], affected_records: [] },
        response: new Response(),
      });
    renderPage(true);
    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (kg)" }), {
      target: { value: "65" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), {
      target: { value: "8" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Log set" }));
    expect(await screen.findByText("Set is safe on this device. Retry when connected.")).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
    const firstOptions = post.mock.calls[0]?.[1] as unknown as {
      params: { header: { "Idempotency-Key": string } };
    };
    const firstKey = firstOptions.params.header["Idempotency-Key"];

    fireEvent.click(screen.getByRole("button", { name: "Retry save" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    const retryOptions = post.mock.calls[1]?.[1] as unknown as {
      params: { header: { "Idempotency-Key": string } };
    };
    expect(retryOptions.params.header["Idempotency-Key"]).toBe(firstKey);
    expect(await screen.findByText("Set saved remotely.")).toBeInTheDocument();
  });

  it("celebrates only achievements returned by the confirmed set response", async () => {
    vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: {
        set: loggedSet,
        new_achievements: [
          {
            id: "achievement-1",
            achievement_type: "personal_record",
            exercise_id: exercise.id,
            title: "New max load",
            message: "Incline Press: 65 kg.",
            achieved_at: "2026-07-13T12:00:00Z",
            public: true,
          },
        ],
        affected_records: [],
      },
      response: new Response(),
    });
    renderPage(true);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (kg)" }), {
      target: { value: "65" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log set" }));

    const dialog = await screen.findByRole("dialog", { name: "Personal best!" });
    expect(dialog).toHaveTextContent("New max load");
    expect(dialog).toHaveTextContent("Incline Press: 65 kg.");
    expect(screen.getByRole("button", { name: "Keep training" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Keep training" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("carries an accepted growth target into the matching journal exercise", async () => {
    sessionStorage.setItem(
      `levels:growth:accepted:${exercise.id}`,
      JSON.stringify({
        suggestion: {
          exercise_id: exercise.id,
          exercise_name: exercise.name,
          suggestion_type: "add_rep",
          suggested_delta: 1,
          delta_unit: "rep",
          confidence: "medium",
          explanation: ["Aim for one additional rep with stable form."],
          source_session_ids: ["session-source"],
        },
      }),
    );
    renderPage(true);
    expect((await screen.findByText(/Growth target:/)).parentElement).toHaveTextContent(
      "Aim for one additional rep with stable form.",
    );
  });
});
