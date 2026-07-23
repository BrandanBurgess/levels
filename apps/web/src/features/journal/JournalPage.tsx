import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import {
  formatWeight,
  weightFromKilograms,
  weightToKilograms,
  weightUnit,
  type UnitPreference,
} from "../../utils/units";
import "./JournalPage.css";

type WorkoutSession = components["schemas"]["WorkoutSession"];
type SessionExercise = components["schemas"]["SessionExercise"];
type SetLog = components["schemas"]["SetLog"];
type Exercise = components["schemas"]["Exercise"];
type MeasurementType = Exercise["measurement_type"];
type SetType = components["schemas"]["SetWrite"]["set_type"];
type Achievement = components["schemas"]["Achievement"];
type GrowthSuggestion = components["schemas"]["GrowthSuggestion"];

type SetDraft = {
  setType: SetType;
  load: string;
  reps: string;
  rir: string;
  duration: string;
  distance: string;
  rounds: string;
  form: string;
  pain: boolean;
};

type StoredSetDraft = {
  values: SetDraft;
  idempotencyKey: string;
  updatedAt: string;
  unitPreference?: UnitPreference;
};

const emptyDraft: SetDraft = {
  setType: "working",
  load: "",
  reps: "",
  rir: "2",
  duration: "",
  distance: "",
  rounds: "",
  form: "4",
  pain: false,
};

function setDraftKey(sessionId: string, itemId: string) {
  return `levels:journal:set:${sessionId}:${itemId}`;
}

function loadSetDraft(
  sessionId: string,
  itemId: string,
  units: UnitPreference,
): StoredSetDraft {
  try {
    const value = localStorage.getItem(setDraftKey(sessionId, itemId));
    if (value) {
      const stored = JSON.parse(value) as StoredSetDraft;
      const storedUnits = stored.unitPreference ?? "metric";
      const load = stored.values.load;
      return {
        ...stored,
        unitPreference: units,
        values: {
          ...stored.values,
          load: load !== "" && storedUnits !== units
            ? weightFromKilograms(weightToKilograms(Number(load), storedUnits), units).toString()
            : load,
        },
      };
    }
  } catch {
    // Storage can be unavailable in hardened browser modes; the in-memory draft still works.
  }
  return {
    values: emptyDraft,
    idempotencyKey: crypto.randomUUID(),
    updatedAt: new Date().toISOString(),
    unitPreference: units,
  };
}

function persistSetDraft(sessionId: string, itemId: string, draft: StoredSetDraft) {
  try {
    localStorage.setItem(setDraftKey(sessionId, itemId), JSON.stringify(draft));
  } catch {
    // Keep editing available even when browser storage is blocked or full.
  }
}

function clearSetDraft(sessionId: string, itemId: string) {
  try {
    localStorage.removeItem(setDraftKey(sessionId, itemId));
  } catch {
    // The confirmed server copy is authoritative even if storage cleanup is blocked.
  }
}

async function loadSessions() {
  const { data, error } = await apiClient.GET("/sessions", {
    params: { query: {} },
  });
  if (!data || error) throw new Error("Session request failed");
  return data;
}

async function loadExercises() {
  const { data, error } = await apiClient.GET("/exercises", { params: { query: {} } });
  if (!data || error) throw new Error("Exercise request failed");
  return data;
}

async function loadToday() {
  const { data, error } = await apiClient.GET("/today", { params: { query: {} } });
  if (!data || error) throw new Error("Today request failed");
  return data;
}

function number(value: string) {
  return value === "" ? null : Number(value);
}

function setSummary(set: SetLog, units: UnitPreference) {
  if (set.load_kg != null || set.reps != null) {
    return `${set.load_kg != null ? formatWeight(set.load_kg, units) : "Bodyweight"} × ${set.reps ?? 0}`;
  }
  if (set.duration_seconds != null) return `${set.duration_seconds} sec`;
  if (set.distance_meters != null) return `${set.distance_meters} m`;
  return `${set.rounds ?? 0} rounds`;
}

function acceptedGrowthSuggestion(exerciseId: string): GrowthSuggestion | undefined {
  try {
    const stored = sessionStorage.getItem(`levels:growth:accepted:${exerciseId}`);
    if (!stored) return undefined;
    return (JSON.parse(stored) as { suggestion: GrowthSuggestion }).suggestion;
  } catch {
    return undefined;
  }
}

function draftFromSet(set: SetLog, units: UnitPreference): SetDraft {
  return {
    setType: set.set_type,
    load: set.load_kg == null ? "" : weightFromKilograms(set.load_kg, units).toString(),
    reps: set.reps?.toString() ?? "",
    rir: set.rir?.toString() ?? "",
    duration: set.duration_seconds?.toString() ?? "",
    distance: set.distance_meters?.toString() ?? "",
    rounds: set.rounds?.toString() ?? "",
    form: set.form_quality?.toString() ?? "",
    pain: set.pain_flag,
  };
}

function RecordCelebration({
  achievements,
  onDismiss,
  returnFocus,
}: {
  achievements: Achievement[];
  onDismiss: () => void;
  returnFocus?: HTMLElement | null;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousFocus.current = returnFocus
      ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    closeButton.current?.focus();
    return () => previousFocus.current?.focus();
  }, [returnFocus]);

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onDismiss();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialog.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    );
    if (!focusable.length) {
      event.preventDefault();
      dialog.current?.focus();
      return;
    }
    const first = focusable[0]!;
    const last = focusable.at(-1)!;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="celebration-backdrop" role="presentation">
      <section
        aria-labelledby="celebration-title"
        aria-modal="true"
        className="record-celebration"
        onKeyDown={handleKeyDown}
        ref={dialog}
        role="dialog"
        tabIndex={-1}
      >
        <div aria-hidden="true" className="celebration-confetti">
          {Array.from({ length: 12 }, (_, index) => <i key={index} />)}
        </div>
        <p className="book-kicker">SERVER CONFIRMED</p>
        <h2 id="celebration-title">
          {achievements.length === 1 ? "Personal best!" : `${achievements.length} personal bests!`}
        </h2>
        <ul>
          {achievements.map((achievement) => (
            <li key={achievement.id}>
              <strong>{achievement.title}</strong>
              <span>{achievement.message}</span>
            </li>
          ))}
        </ul>
        <button className="button button--primary" onClick={onDismiss} ref={closeButton} type="button">
          Keep training
        </button>
      </section>
    </div>
  );
}

function SetEntry({
  sessionId,
  item,
  measurement,
  onSaved,
  units,
}: {
  sessionId: string;
  item: SessionExercise;
  measurement: MeasurementType;
  onSaved: () => Promise<void>;
  units: UnitPreference;
}) {
  const [restored] = useState(() => loadSetDraft(sessionId, item.id, units));
  const [draft, setDraft] = useState<SetDraft>(restored.values);
  const [idempotencyKey, setIdempotencyKey] = useState(restored.idempotencyKey);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string>();
  const [retryAvailable, setRetryAvailable] = useState(false);
  const [celebration, setCelebration] = useState<Achievement[]>([]);
  const [editingSet, setEditingSet] = useState<SetLog>();
  const celebrationTrigger = useRef<HTMLElement | null>(null);
  const lastSet = item.sets.at(-1);

  function updateDraft(values: SetDraft) {
    const key = crypto.randomUUID();
    setDraft(values);
    setIdempotencyKey(key);
    setRetryAvailable(false);
    persistSetDraft(sessionId, item.id, {
      values,
      idempotencyKey: key,
      updatedAt: new Date().toISOString(),
      unitPreference: units,
    });
  }

  function adjust(field: "load" | "reps", amount: number) {
    updateDraft({
      ...draft,
      [field]: String(Math.max(0, Number(draft[field] || 0) + amount)),
    });
  }

  async function save(event?: FormEvent, duplicate?: SetLog) {
    event?.preventDefault();
    celebrationTrigger.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    setSaving(true);
    setMessage(undefined);
    const value = duplicate ? draftFromSet(duplicate, units) : draft;
    try {
      const body = {
        session_exercise_id: item.id,
        set_type: value.setType,
        load_kg: duplicate
          ? duplicate.load_kg ?? null
          : value.load === "" ? null : weightToKilograms(Number(value.load), units),
        reps: number(value.reps),
        rir: number(value.rir),
        duration_seconds: number(value.duration),
        distance_meters: number(value.distance),
        rounds: number(value.rounds),
        form_quality: number(value.form),
        pain_flag: value.pain,
      };
      const { data, error } = editingSet && !duplicate
        ? await apiClient.PATCH("/sets/{set_id}", {
            params: { path: { set_id: editingSet.id } },
            body,
          })
        : await apiClient.POST("/sessions/{session_id}/sets", {
            params: {
              path: { session_id: sessionId },
              header: { "Idempotency-Key": duplicate ? crypto.randomUUID() : idempotencyKey },
            },
            body,
          });
      if (!data || error) throw new Error("Set write failed");
      clearSetDraft(sessionId, item.id);
      setDraft(draftFromSet(data.set, units));
      setIdempotencyKey(crypto.randomUUID());
      setRetryAvailable(false);
      setMessage(
        duplicate ? "Previous set duplicated." : editingSet ? "Set changes saved." : "Set saved remotely.",
      );
      setEditingSet(undefined);
      if (data.new_achievements.length) setCelebration(data.new_achievements);
      await onSaved();
    } catch {
      setRetryAvailable(!duplicate);
      setMessage(
        duplicate
          ? "The duplicate was not saved. Try again when connected."
          : "Set is safe on this device. Retry when connected.",
      );
    } finally {
      setSaving(false);
    }
  }

  function startEditing(set: SetLog) {
    setEditingSet(set);
    setDraft(draftFromSet(set, units));
    setRetryAvailable(false);
    setMessage(`Editing set ${set.sequence}.`);
  }

  function cancelEditing() {
    setEditingSet(undefined);
    setDraft(lastSet ? draftFromSet(lastSet, units) : emptyDraft);
    setRetryAvailable(false);
    setMessage("Set edit cancelled.");
    clearSetDraft(sessionId, item.id);
  }

  async function deleteSet(set: SetLog) {
    if (!window.confirm(`Delete set ${set.sequence}? This cannot be undone.`)) return;
    setSaving(true);
    setMessage(undefined);
    try {
      const { error, response } = await apiClient.DELETE("/sets/{set_id}", {
        params: { path: { set_id: set.id } },
      });
      if (error || !response.ok) throw new Error("Set delete failed");
      if (editingSet?.id === set.id) setEditingSet(undefined);
      setMessage(`Set ${set.sequence} deleted.`);
      await onSaved();
    } catch {
      setMessage(`Set ${set.sequence} could not be deleted.`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {item.sets.length ? (
        <ul className="logged-sets">
          {item.sets.map((set) => (
            <li key={set.id}>
              <span>Set {set.sequence}</span>
              <strong>{setSummary(set, units)}</strong>
              <small>{set.set_type}</small>
              <span className="logged-set-actions">
                <button
                  aria-label={`Edit set ${set.sequence}`}
                  disabled={saving}
                  onClick={() => startEditing(set)}
                  type="button"
                >
                  Edit
                </button>
                <button
                  aria-label={`Delete set ${set.sequence}`}
                  disabled={saving}
                  onClick={() => void deleteSet(set)}
                  type="button"
                >
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <form className="set-entry" onSubmit={(event) => void save(event)}>
      <div className="set-entry__fields">
        {measurement === "load_reps" ? (
          <div className="set-field">
            <label htmlFor={`${item.id}-load`}>Weight ({weightUnit(units)})</label>
            <span className="stepper-input">
              <button aria-label={`Decrease ${item.display_name} weight`} onClick={() => adjust("load", units === "imperial" ? -5 : -2.5)} type="button">−</button>
              <input id={`${item.id}-load`} inputMode="decimal" min="0" onChange={(event) => updateDraft({ ...draft, load: event.target.value })} required step="any" type="number" value={draft.load} />
              <button aria-label={`Increase ${item.display_name} weight`} onClick={() => adjust("load", units === "imperial" ? 5 : 2.5)} type="button">+</button>
            </span>
          </div>
        ) : null}
        {measurement === "load_reps" || measurement === "bodyweight_reps" ? (
          <div className="set-field">
            <label htmlFor={`${item.id}-reps`}>Reps</label>
            <span className="stepper-input">
              <button aria-label={`Decrease ${item.display_name} reps`} onClick={() => adjust("reps", -1)} type="button">−</button>
              <input id={`${item.id}-reps`} inputMode="numeric" min="0" onChange={(event) => updateDraft({ ...draft, reps: event.target.value })} required type="number" value={draft.reps} />
              <button aria-label={`Increase ${item.display_name} reps`} onClick={() => adjust("reps", 1)} type="button">+</button>
            </span>
          </div>
        ) : null}
        {measurement === "duration" ? <label htmlFor={`${item.id}-duration`}>Time (seconds)<input id={`${item.id}-duration`} inputMode="numeric" min="0" onChange={(event) => updateDraft({ ...draft, duration: event.target.value })} required type="number" value={draft.duration} /></label> : null}
        {measurement === "distance" ? <label htmlFor={`${item.id}-distance`}>Distance (metres)<input id={`${item.id}-distance`} inputMode="decimal" min="0" onChange={(event) => updateDraft({ ...draft, distance: event.target.value })} required step="any" type="number" value={draft.distance} /></label> : null}
        {measurement === "rounds" ? <label htmlFor={`${item.id}-rounds`}>Rounds<input id={`${item.id}-rounds`} inputMode="numeric" min="0" onChange={(event) => updateDraft({ ...draft, rounds: event.target.value })} required type="number" value={draft.rounds} /></label> : null}
        <label htmlFor={`${item.id}-rir`}>RIR<input id={`${item.id}-rir`} inputMode="decimal" max="10" min="0" onChange={(event) => updateDraft({ ...draft, rir: event.target.value })} step="any" type="number" value={draft.rir} /></label>
        <label htmlFor={`${item.id}-type`}>Set type<select id={`${item.id}-type`} onChange={(event) => updateDraft({ ...draft, setType: event.target.value as SetType })} value={draft.setType}><option value="warmup">Warm-up</option><option value="working">Working</option><option value="backoff">Back-off</option><option value="drop">Drop</option><option value="failure">Failure</option></select></label>
        <label htmlFor={`${item.id}-form`}>Form (1–5)<input id={`${item.id}-form`} inputMode="numeric" max="5" min="1" onChange={(event) => updateDraft({ ...draft, form: event.target.value })} type="number" value={draft.form} /></label>
        <label className="check-field" htmlFor={`${item.id}-pain`}><input checked={draft.pain} id={`${item.id}-pain`} onChange={(event) => updateDraft({ ...draft, pain: event.target.checked })} type="checkbox" /> Pain noted</label>
      </div>
      <div className="set-entry__actions">
        <button className="button button--primary" disabled={saving} type="submit">{saving ? "Saving…" : editingSet ? "Save set changes" : "Log set"}</button>
        {editingSet ? <button className="button" disabled={saving} onClick={cancelEditing} type="button">Cancel edit</button> : null}
        {retryAvailable ? <button className="button" disabled={saving} onClick={() => void save()} type="button">Retry save</button> : null}
        {lastSet && !editingSet ? <button className="button" disabled={saving} onClick={() => void save(undefined, lastSet)} type="button">Duplicate previous</button> : null}
        {message ? <span role="status">{message}</span> : null}
      </div>
      {celebration.length ? (
        <RecordCelebration achievements={celebration} onDismiss={() => setCelebration([])} returnFocus={celebrationTrigger.current} />
      ) : null}
      </form>
    </>
  );
}

type NotesDraft = { notesPrivate: string; updatedAt: string };

function notesDraftKey(sessionId: string) {
  return `levels:journal:notes:${sessionId}`;
}

function loadNotesDraft(session: WorkoutSession): NotesDraft {
  try {
    const value = localStorage.getItem(notesDraftKey(session.id));
    if (value) return JSON.parse(value) as NotesDraft;
  } catch {
    // Fall back to the last confirmed server notes.
  }
  return {
    notesPrivate: session.notes_private ?? "",
    updatedAt: new Date().toISOString(),
  };
}

function persistNotesDraft(sessionId: string, value: NotesDraft | null) {
  try {
    if (value) localStorage.setItem(notesDraftKey(sessionId), JSON.stringify(value));
    else localStorage.removeItem(notesDraftKey(sessionId));
  } catch {
    // Keep the form usable when storage is unavailable.
  }
}

function SessionBook({
  session,
  exercises,
  sessions,
  refresh,
  units,
}: {
  session: WorkoutSession;
  exercises: Exercise[];
  sessions: WorkoutSession[];
  refresh: () => Promise<void>;
  units: UnitPreference;
}) {
  const [editingWorkout, setEditingWorkout] = useState(false);
  const [substitutes, setSubstitutes] = useState<Record<string, string>>({});
  const [plannedSets, setPlannedSets] = useState<Record<string, string>>({});
  const [newExercise, setNewExercise] = useState("");
  const [restoredNotes] = useState(() => loadNotesDraft(session));
  const [notesPrivate, setNotesPrivate] = useState(restoredNotes.notesPrivate);
  const [message, setMessage] = useState<string>();
  const [editorMessage, setEditorMessage] = useState<{ error: boolean; text: string }>();
  const [editorBusy, setEditorBusy] = useState(false);
  const completionKey = useRef(crypto.randomUUID());
  const exerciseMap = new Map(exercises.map((exercise) => [exercise.id, exercise]));
  const visibleExercises = session.status === "in_progress"
    ? session.exercises.filter((item) => item.removed_at == null)
    : session.exercises;

  function updateNotes(value: string) {
    setNotesPrivate(value);
    persistNotesDraft(session.id, {
      notesPrivate: value,
      updatedAt: new Date().toISOString(),
    });
  }

  async function runEditorCommand(
    command: () => Promise<{ error?: unknown; response: Response }>,
    successMessage: string,
  ) {
    setEditorBusy(true);
    setEditorMessage(undefined);
    try {
      const { error, response } = await command();
      if (error || !response.ok) {
        if (response.status === 409) {
          await refresh();
          setEditorMessage({
            error: true,
            text: "This workout changed elsewhere. The latest version is loaded; try again.",
          });
        } else {
          setEditorMessage({ error: true, text: "Workout changes could not be saved. Try again." });
        }
        return false;
      }
      await refresh();
      setEditorMessage({ error: false, text: successMessage });
      return true;
    } catch {
      setEditorMessage({ error: true, text: "Workout changes could not be saved. Check your connection and try again." });
      return false;
    } finally {
      setEditorBusy(false);
    }
  }

  async function substitute(item: SessionExercise) {
    const exerciseId = substitutes[item.id];
    if (!exerciseId) return;
    await runEditorCommand(
      () => apiClient.POST("/sessions/{session_id}/exercises", {
        params: { path: { session_id: session.id } },
        body: {
          exercise_id: exerciseId,
          expected_version: session.version,
          replace_session_exercise_id: item.id,
          substitution_reason: "Member substitution",
        },
      }),
      "Exercise substituted for this workout.",
    );
  }

  async function addExercise() {
    if (!newExercise) return;
    const saved = await runEditorCommand(
      () => apiClient.POST("/sessions/{session_id}/exercises", {
        params: { path: { session_id: session.id } },
        body: { exercise_id: newExercise, expected_version: session.version },
      }),
      "Exercise added to this workout.",
    );
    if (saved) {
      setNewExercise("");
    }
  }

  async function updateExercise(item: SessionExercise) {
    const value = Number(plannedSets[item.id] ?? item.planned_sets);
    if (!Number.isInteger(value) || value < 1) {
      setEditorMessage({ error: true, text: "Planned sets must be a whole number of at least 1." });
      return;
    }
    await runEditorCommand(
      () => apiClient.PATCH("/sessions/{session_id}/exercises/{session_exercise_id}", {
        params: { path: { session_id: session.id, session_exercise_id: item.id } },
        body: { expected_version: session.version, planned_sets: value },
      }),
      `${item.display_name} settings saved.`,
    );
  }

  async function removeExercise(item: SessionExercise) {
    const confirmLoggedSets = item.sets.length > 0;
    if (confirmLoggedSets && !window.confirm(
      `Remove ${item.display_name} and its ${item.sets.length} logged ${item.sets.length === 1 ? "set" : "sets"}?`,
    )) return;
    await runEditorCommand(
      () => apiClient.DELETE("/sessions/{session_id}/exercises/{session_exercise_id}", {
        params: {
          path: { session_id: session.id, session_exercise_id: item.id },
          query: { expected_version: session.version, confirm_logged_sets: confirmLoggedSets },
        },
      }),
      `${item.display_name} removed from this workout.`,
    );
  }

  async function moveExercise(index: number, direction: -1 | 1) {
    const destination = index + direction;
    if (destination < 0 || destination >= visibleExercises.length) return;
    const reordered = visibleExercises.map((item) => item.id);
    const sourceId = reordered[index]!;
    const destinationId = reordered[destination]!;
    reordered[index] = destinationId;
    reordered[destination] = sourceId;
    await runEditorCommand(
      () => apiClient.POST("/sessions/{session_id}/exercises/reorder", {
        params: { path: { session_id: session.id } },
        body: {
          expected_version: session.version,
          ordered_session_exercise_ids: reordered,
        },
      }),
      "Exercise order updated.",
    );
  }

  async function saveSession(status?: "in_progress" | "completed") {
    try {
      const { error: patchError } = await apiClient.PATCH("/sessions/{session_id}", {
        params: { path: { session_id: session.id } },
        body: {
          ...(status === "in_progress" ? { status } : {}),
          notes_private: notesPrivate,
        },
      });
      if (patchError) throw new Error("Session write failed");
      if (status === "completed") {
        const { error: completionError } = await apiClient.POST(
          "/sessions/{session_id}/complete",
          {
            params: {
              path: { session_id: session.id },
              header: { "Idempotency-Key": completionKey.current },
            },
          },
        );
        if (completionError) throw new Error("Session completion failed");
        completionKey.current = crypto.randomUUID();
      }
      persistNotesDraft(session.id, null);
      if (status === "completed") {
        setEditingWorkout(false);
        setEditorMessage(undefined);
      }
      setMessage(status === "completed" ? "Workout completed." : status === "in_progress" ? "Workout resumed." : "Notes saved remotely.");
      await refresh();
    } catch {
      setMessage("Notes are safe on this device. Retry when connected.");
    }
  }

  return (
    <section className="journal-book" aria-labelledby="session-title">
      <div className="journal-book__spine" aria-hidden="true" />
      <div className="journal-page journal-page--left">
        <p className="book-kicker">{session.session_date_local}</p>
        <h2 id="session-title">{session.title}</h2>
        <p className={`session-status session-status--${session.status}`}>{session.status.replace("_", " ")}</p>
        <p className="draft-hint">Saved on this device as you type and remotely when the field loses focus.</p>
        <label className="notes-field">Private notes<textarea onBlur={() => void saveSession()} onChange={(event) => updateNotes(event.target.value)} rows={5} value={notesPrivate} /></label>
        <div className="book-actions">
          <button className="button" onClick={() => void saveSession()} type="button">Save notes</button>
          {session.status === "in_progress" ? (
            <button
              aria-expanded={editingWorkout}
              className="button"
              onClick={() => {
                setEditingWorkout((current) => !current);
                setEditorMessage(undefined);
              }}
              type="button"
            >
              {editingWorkout ? "Done editing" : "Edit workout"}
            </button>
          ) : null}
          {session.status === "completed" ? <button className="button button--primary" onClick={() => void saveSession("in_progress")} type="button">Resume workout</button> : <button className="button button--primary" onClick={() => void saveSession("completed")} type="button">Complete workout</button>}
        </div>
        {message ? <p className="ink-status" role="status">{message}</p> : null}
      </div>

      <div className="journal-page journal-page--right">
        <ol className="journal-exercises">
          {visibleExercises.map((item, index) => {
            const catalogExercise = exerciseMap.get(item.exercise_id);
            const acceptedGrowth = acceptedGrowthSuggestion(item.exercise_id);
            const previous = sessions.find((candidate) => candidate.id !== session.id && candidate.status === "completed" && candidate.exercises.some((exercise) => exercise.exercise_id === item.exercise_id));
            const previousItem = previous?.exercises.find((exercise) => exercise.exercise_id === item.exercise_id);
            return (
              <li key={item.id}>
                <div className="journal-exercise__heading">
                  <div><span>{item.sequence}</span><h3>{item.display_name}</h3></div>
                  <small>{item.rep_min != null ? `${item.rep_min}–${item.rep_max ?? item.rep_min} reps` : catalogExercise?.measurement_type.replaceAll("_", " ")}</small>
                </div>
                {acceptedGrowth ? <p className="accepted-guidance"><strong>Growth target:</strong> {acceptedGrowth.explanation.at(-1)}</p> : null}
                {previousItem?.sets.at(-1) ? <p className="previous-performance">Previous: {setSummary(previousItem.sets.at(-1)!, units)}</p> : null}
                {item.sets.length && session.status !== "in_progress" ? <ul className="logged-sets">{item.sets.map((set) => <li key={set.id}><span>Set {set.sequence}</span><strong>{setSummary(set, units)}</strong><small>{set.set_type}</small></li>)}</ul> : null}
                {session.status === "in_progress" && catalogExercise ? <SetEntry item={item} measurement={catalogExercise.measurement_type} onSaved={refresh} sessionId={session.id} units={units} /> : null}
                {session.status === "in_progress" && editingWorkout ? (
                  <div className="workout-edit-card">
                    <div className="workout-edit-card__row">
                      <label htmlFor={`planned-sets-${item.id}`}>Planned sets
                        <input id={`planned-sets-${item.id}`} min="1" onChange={(event) => setPlannedSets({ ...plannedSets, [item.id]: event.target.value })} type="number" value={plannedSets[item.id] ?? String(item.planned_sets)} />
                      </label>
                      <button className="button" disabled={editorBusy} onClick={() => void updateExercise(item)} type="button">Save settings</button>
                    </div>
                    <div className="substitution-control"><label htmlFor={`substitute-${item.id}`}>Substitute exercise</label><select id={`substitute-${item.id}`} onChange={(event) => setSubstitutes({ ...substitutes, [item.id]: event.target.value })} value={substitutes[item.id] ?? ""}><option value="">Choose movement</option>{exercises.filter((exercise) => exercise.id !== item.exercise_id).map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select><button className="button" disabled={editorBusy || !substitutes[item.id]} onClick={() => void substitute(item)} type="button">Substitute</button></div>
                    <div className="workout-edit-card__actions" aria-label={`${item.display_name} workout controls`}>
                      <button aria-label={`Move ${item.display_name} up`} className="button" disabled={editorBusy || index === 0} onClick={() => void moveExercise(index, -1)} type="button">Move up</button>
                      <button aria-label={`Move ${item.display_name} down`} className="button" disabled={editorBusy || index === visibleExercises.length - 1} onClick={() => void moveExercise(index, 1)} type="button">Move down</button>
                      <button aria-label={`Remove ${item.display_name}`} className="button button--danger" disabled={editorBusy} onClick={() => void removeExercise(item)} type="button">Remove</button>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
        {session.status === "in_progress" && editingWorkout ? <div className="add-exercise workout-edit-add"><label htmlFor="add-exercise">Add exercise</label><select id="add-exercise" onChange={(event) => setNewExercise(event.target.value)} value={newExercise}><option value="">Choose movement</option>{exercises.map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select><button className="button" disabled={editorBusy || !newExercise} onClick={() => void addExercise()} type="button">Add</button></div> : null}
        {editorMessage ? <p className="workout-editor-message" role={editorMessage.error ? "alert" : "status"}>{editorMessage.text}</p> : null}
      </div>
    </section>
  );
}

export function JournalPage() {
  const { user } = useAuth();
  const units = user?.preferred_units ?? "imperial";
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: loadSessions });
  const exercisesQuery = useQuery({ queryKey: ["exercises", "journal"], queryFn: loadExercises });
  const todayQuery = useQuery({ queryKey: ["today"], queryFn: loadToday });
  const [selectedId, setSelectedId] = useState<string>();
  const [starting, setStarting] = useState(false);
  const sessions = sessionsQuery.data ?? [];
  const selected = sessions.find((session) => session.id === selectedId) ?? sessions.find((session) => session.status === "in_progress") ?? sessions[0];

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }

  async function startToday() {
    const day = todayQuery.data?.effective_day;
    if (!day) return;
    setStarting(true);
    const { data } = await apiClient.POST("/sessions", {
      params: { header: { "Idempotency-Key": crypto.randomUUID() } },
      body: { split_day_id: day.id, expected_schedule_version: todayQuery.data!.schedule_version },
    });
    setStarting(false);
    if (data) {
      setSelectedId(data.id);
      await refresh();
    }
  }

  return (
    <article className="page-shell journal-shell">
      <header className="page-heading journal-heading"><p className="eyebrow">TRAINING LOG</p><h1>Journal</h1><p>Open today’s workout, record the work, and keep every session legible.</p></header>
      {todayQuery.data?.effective_day && !sessions.some((session) => session.status === "in_progress") ? <button className="button button--primary start-workout" disabled={starting} onClick={() => void startToday()} type="button">{starting ? "Opening workout…" : `Start ${todayQuery.data.effective_day.name}`}</button> : null}
      {sessionsQuery.isPending || exercisesQuery.isPending ? <LoadingState /> : null}
      {sessionsQuery.isError || exercisesQuery.isError ? <ErrorState message="The workout journal could not be loaded." onRetry={() => void Promise.all([sessionsQuery.refetch(), exercisesQuery.refetch()])} /> : null}
      {sessions.length ? <nav aria-label="Workout sessions" className="session-tabs">{sessions.map((session) => <button aria-pressed={selected?.id === session.id} key={session.id} onClick={() => setSelectedId(session.id)} type="button"><strong>{session.title}</strong><span>{session.session_date_local} · {session.status.replace("_", " ")}</span></button>)}</nav> : null}
      {!sessionsQuery.isPending && sessions.length === 0 ? <EmptyState title="No sessions yet">Start today’s scheduled workout to open the first page.</EmptyState> : null}
      {selected && exercisesQuery.data ? <SessionBook exercises={exercisesQuery.data} key={selected.id} refresh={refresh} session={selected} sessions={sessions} units={units} /> : null}
    </article>
  );
}
