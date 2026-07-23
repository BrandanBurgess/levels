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
  scope: "global" as const,
  can_edit: false,
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

const cableRow = {
  ...exercise,
  id: "cable_row",
  slug: "cable-row",
  name: "Cable Row",
  aliases: [],
  variation_group: "cable_row",
  movement_pattern: "horizontal_pull",
  equipment: "cable",
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
  version: 3,
  session_date_local: "2026-07-13",
  started_at: "2026-07-13T11:00:00Z",
  status: "in_progress" as const,
  title: "Upper A",
  exercises: [
    {
      id: "session-exercise-1",
      exercise_id: exercise.id,
      display_name: exercise.name,
      variation_group: exercise.variation_group,
      sequence: 1,
      planned_sets: 3,
      item_type: "main",
      optional: false,
      rep_min: 6,
      rep_max: 10,
      sets: [loggedSet],
    },
  ],
};

const today = {
  local_date: "2026-07-13",
  schedule_version: 5,
  effective_day: {
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

function renderPage(
  isAuthenticated: boolean,
  sessions: WorkoutSession[] = [activeSession],
  catalog = [exercise],
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth: AuthState = {
    ...(isAuthenticated ? { admin: { displayName: "Brandan" } } : {}),
    ...(isAuthenticated ? {
      user: {
        id: "user-1",
        email: "member@example.com",
        display_name: "Brandan",
        role: "member" as const,
        account_status: "active" as const,
        timezone: "America/Toronto",
        preferred_units: "imperial" as const,
      },
    } : {}),
    isAuthenticated,
    isSubmitting: false,
    login: vi.fn(async () => false),
    logout: vi.fn(),
  };
  vi.spyOn(apiClient, "GET").mockImplementation(async (path) => {
    if (path === "/sessions") return { data: sessions, response: new Response() };
    if (path === "/exercises") return { data: catalog, response: new Response() };
    return { data: today, response: new Response() };
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
  it("shows a completed member journal", async () => {
    const completed = {
      ...activeSession,
      status: "completed" as const,
    };
    renderPage(true, [completed]);

    expect(await screen.findByRole("heading", { name: "Upper A" })).toBeInTheDocument();
    expect(screen.getByText("132.28 lb × 8")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit workout" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit set 1" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Private notes")).toBeInTheDocument();
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
        expect.objectContaining({ body: { split_day_id: "day-1", expected_schedule_version: 5 } }),
      ),
    );
  });

  it("provides mobile numeric inputs, fast controls, and set duplication", async () => {
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: { set: loggedSet, new_achievements: [], affected_records: [] },
      response: new Response(),
    });
    renderPage(true);

    const weight = await screen.findByRole("spinbutton", { name: "Weight (lb)" });
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
          load_kg: 2.267962,
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

  it("edits and deletes logged sets through owner controls", async () => {
    const editedSet = { ...loggedSet, load_kg: 62.5 };
    const patch = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: { set: editedSet, new_achievements: [], affected_records: [] },
      response: new Response(),
    });
    const remove = vi.spyOn(apiClient, "DELETE").mockResolvedValue({
      data: undefined,
      response: new Response(null, { status: 204 }),
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage(true);

    fireEvent.click(await screen.findByRole("button", { name: "Edit set 1" }));
    expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(132.28);
    fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), {
      target: { value: "220.462262" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save set changes" }));

    await waitFor(() =>
      expect(patch).toHaveBeenCalledWith(
        "/sets/{set_id}",
        expect.objectContaining({
          params: { path: { set_id: "set-1" } },
          body: expect.objectContaining({ load_kg: 100, reps: 8 }),
        }),
      ),
    );
    expect(await screen.findByText("Set changes saved.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete set 1" }));
    await waitFor(() =>
      expect(remove).toHaveBeenCalledWith("/sets/{set_id}", {
        params: { path: { set_id: "set-1" } },
      }),
    );
    expect(await screen.findByText("Set 1 deleted.")).toBeInTheDocument();
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

    expect(screen.queryByRole("button", { name: "Substitute" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Edit workout" }));
    expect(screen.getByRole("button", { name: "Substitute" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Complete workout" }));
    await waitFor(() => expect(patch).toHaveBeenCalled());
    expect(patch).toHaveBeenCalledWith(
      "/sessions/{session_id}",
      expect.objectContaining({ body: expect.not.objectContaining({ status: "completed" }) }),
    );
    expect(post).toHaveBeenCalledWith(
      "/sessions/{session_id}/complete",
      expect.objectContaining({
        params: {
          path: { session_id: "session-1" },
          header: { "Idempotency-Key": expect.any(String) },
        },
      }),
    );
  });

  it("edits an active workout with versioned add, update, substitute, remove, and reorder commands", async () => {
    const baseItem = {
      ...activeSession.exercises[0]!,
      sets: [...activeSession.exercises[0]!.sets],
    };
    const session: WorkoutSession = {
      ...activeSession,
      exercises: [
        baseItem,
        {
          ...baseItem,
          id: "session-exercise-2",
          exercise_id: cableRow.id,
          display_name: cableRow.name,
          variation_group: cableRow.variation_group,
          sequence: 2,
          sets: [],
        },
      ],
    };
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: session.exercises[0]!,
      response: new Response(),
    });
    const patch = vi.spyOn(apiClient, "PATCH").mockResolvedValue({
      data: session,
      response: new Response(),
    });
    const remove = vi.spyOn(apiClient, "DELETE").mockImplementation(async () => {
      session.exercises[0]!.removed_at = "2026-07-13T12:30:00Z";
      return { data: session, response: new Response() };
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage(true, [session], [exercise, cableRow]);

    expect(screen.queryByLabelText("Planned sets")).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Edit workout" }));
    expect(screen.getAllByRole("button", { name: "Log set" })).toHaveLength(2);

    fireEvent.change(screen.getAllByLabelText("Planned sets")[0]!, { target: { value: "4" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Save settings" })[0]!);
    await waitFor(() => expect(patch).toHaveBeenCalledWith(
      "/sessions/{session_id}/exercises/{session_exercise_id}",
      {
        params: { path: { session_id: "session-1", session_exercise_id: "session-exercise-1" } },
        body: { expected_version: 3, planned_sets: 4 },
      },
    ));

    fireEvent.change(screen.getByLabelText("Substitute exercise", { selector: "select#substitute-session-exercise-1" }), { target: { value: cableRow.id } });
    fireEvent.click(screen.getAllByRole("button", { name: "Substitute" })[0]!);
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/sessions/{session_id}/exercises",
      expect.objectContaining({
        body: expect.objectContaining({
          expected_version: 3,
          exercise_id: cableRow.id,
          replace_session_exercise_id: "session-exercise-1",
        }),
      }),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Move Incline Press down" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/sessions/{session_id}/exercises/reorder",
      {
        params: { path: { session_id: "session-1" } },
        body: {
          expected_version: 3,
          ordered_session_exercise_ids: ["session-exercise-2", "session-exercise-1"],
        },
      },
    ));

    fireEvent.click(screen.getByRole("button", { name: "Remove Incline Press" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith(
      "/sessions/{session_id}/exercises/{session_exercise_id}",
      {
        params: {
          path: { session_id: "session-1", session_exercise_id: "session-exercise-1" },
          query: { expected_version: 3, confirm_logged_sets: true },
        },
      },
    ));
    expect(window.confirm).toHaveBeenCalledWith("Remove Incline Press and its 1 logged set?");
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Incline Press" })).not.toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Add exercise"), { target: { value: cableRow.id } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/sessions/{session_id}/exercises",
      {
        params: { path: { session_id: "session-1" } },
        body: { exercise_id: cableRow.id, expected_version: 3 },
      },
    ));
  });

  it("announces a version conflict and refreshes the authoritative session", async () => {
    vi.spyOn(apiClient, "POST").mockResolvedValue({
      error: { detail: "Conflict" },
      response: new Response(null, { status: 409 }),
    } as never);
    renderPage(true, [activeSession], [exercise, cableRow]);

    fireEvent.click(await screen.findByRole("button", { name: "Edit workout" }));
    const sessionLoadCount = () => (
      apiClient.GET as unknown as { mock: { calls: [string, ...unknown[]][] } }
    ).mock.calls.filter(([path]) => path === "/sessions").length;
    const loadsBeforeConflict = sessionLoadCount();
    fireEvent.change(screen.getByLabelText("Add exercise"), { target: { value: cableRow.id } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The latest version is loaded; try again.",
    );
    await waitFor(() => expect(sessionLoadCount()).toBeGreaterThan(loadsBeforeConflict));
  });

  it("restores the latest local set and notes draft after a refresh", async () => {
    const first = renderPage(true);

    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (lb)" }), {
      target: { value: "82.5" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Private notes" }), {
      target: { value: "Keep shoulder packed" },
    });
    first.unmount();
    renderPage(true);

    expect(await screen.findByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(82.5);
    expect(screen.getByRole("textbox", { name: "Private notes" })).toHaveValue(
      "Keep shoulder packed",
    );
  });

  it("converts an unversioned metric local draft before showing and saving it in pounds", async () => {
    localStorage.setItem(
      "levels:journal:set:session-1:session-exercise-1",
      JSON.stringify({
        values: {
          setType: "working",
          load: "82.5",
          reps: "8",
          rir: "2",
          duration: "",
          distance: "",
          rounds: "",
          form: "4",
          pain: false,
        },
        idempotencyKey: "legacy-key",
        updatedAt: "2026-07-13T12:00:00Z",
      }),
    );
    const post = vi.spyOn(apiClient, "POST").mockResolvedValue({
      data: { set: loggedSet, new_achievements: [], affected_records: [] },
      response: new Response(),
    });
    renderPage(true);

    expect(await screen.findByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(181.88);
    fireEvent.click(screen.getByRole("button", { name: "Log set" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    const options = post.mock.calls[0]![1] as unknown as { body: { load_kg: number } };
    expect(options.body.load_kg).toBeCloseTo(82.5, 2);
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
    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (lb)" }), {
      target: { value: "65" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), {
      target: { value: "8" },
    });

    const logButton = screen.getByRole("button", { name: "Log set" });
    fireEvent.click(logButton);
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
    fireEvent.change(await screen.findByRole("spinbutton", { name: "Weight (lb)" }), {
      target: { value: "65" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), {
      target: { value: "8" },
    });
    const logButton = screen.getByRole("button", { name: "Log set" });
    logButton.focus();
    fireEvent.click(logButton);

    const dialog = await screen.findByRole("dialog", { name: "Personal best!" });
    expect(dialog).toHaveTextContent("New max load");
    expect(dialog).toHaveTextContent("Incline Press: 65 kg.");
    expect(screen.getByRole("button", { name: "Keep training" })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("button", { name: "Keep training" }), { key: "Tab" });
    expect(screen.getByRole("button", { name: "Keep training" })).toHaveFocus();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(logButton).toHaveFocus();
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
