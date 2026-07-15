import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";

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

function loadSetDraft(sessionId: string, itemId: string): StoredSetDraft {
  try {
    const value = localStorage.getItem(setDraftKey(sessionId, itemId));
    if (value) return JSON.parse(value) as StoredSetDraft;
  } catch {
    // Storage can be unavailable in hardened browser modes; the in-memory draft still works.
  }
  return {
    values: emptyDraft,
    idempotencyKey: crypto.randomUUID(),
    updatedAt: new Date().toISOString(),
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

function setSummary(set: SetLog) {
  if (set.load_kg != null || set.reps != null) {
    return `${set.load_kg ?? "Bodyweight"}${set.load_kg != null ? " kg" : ""} × ${set.reps ?? 0}`;
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

function draftFromSet(set: SetLog): SetDraft {
  return {
    setType: set.set_type,
    load: set.load_kg?.toString() ?? "",
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
}: {
  achievements: Achievement[];
  onDismiss: () => void;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => closeButton.current?.focus(), []);
  return (
    <div className="celebration-backdrop" role="presentation">
      <section
        aria-labelledby="celebration-title"
        aria-modal="true"
        className="record-celebration"
        role="dialog"
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
}: {
  sessionId: string;
  item: SessionExercise;
  measurement: MeasurementType;
  onSaved: () => Promise<void>;
}) {
  const [restored] = useState(() => loadSetDraft(sessionId, item.id));
  const [draft, setDraft] = useState<SetDraft>(restored.values);
  const [idempotencyKey, setIdempotencyKey] = useState(restored.idempotencyKey);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string>();
  const [retryAvailable, setRetryAvailable] = useState(false);
  const [celebration, setCelebration] = useState<Achievement[]>([]);
  const [editingSet, setEditingSet] = useState<SetLog>();
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
    setSaving(true);
    setMessage(undefined);
    const value = duplicate ? draftFromSet(duplicate) : draft;
    try {
      const body = {
        session_exercise_id: item.id,
        set_type: value.setType,
        load_kg: number(value.load),
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
      setDraft(draftFromSet(data.set));
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
    setDraft(draftFromSet(set));
    setRetryAvailable(false);
    setMessage(`Editing set ${set.sequence}.`);
  }

  function cancelEditing() {
    setEditingSet(undefined);
    setDraft(lastSet ? draftFromSet(lastSet) : emptyDraft);
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
              <strong>{setSummary(set)}</strong>
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
            <label htmlFor={`${item.id}-load`}>Weight (kg)</label>
            <span className="stepper-input">
              <button aria-label={`Decrease ${item.display_name} weight`} onClick={() => adjust("load", -2.5)} type="button">−</button>
              <input id={`${item.id}-load`} inputMode="decimal" min="0" onChange={(event) => updateDraft({ ...draft, load: event.target.value })} required step="any" type="number" value={draft.load} />
              <button aria-label={`Increase ${item.display_name} weight`} onClick={() => adjust("load", 2.5)} type="button">+</button>
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
        <RecordCelebration achievements={celebration} onDismiss={() => setCelebration([])} />
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
}: {
  session: WorkoutSession;
  exercises: Exercise[];
  sessions: WorkoutSession[];
  refresh: () => Promise<void>;
}) {
  const [substitutes, setSubstitutes] = useState<Record<string, string>>({});
  const [newExercise, setNewExercise] = useState("");
  const [restoredNotes] = useState(() => loadNotesDraft(session));
  const [notesPrivate, setNotesPrivate] = useState(restoredNotes.notesPrivate);
  const [message, setMessage] = useState<string>();
  const exerciseMap = new Map(exercises.map((exercise) => [exercise.id, exercise]));

  function updateNotes(value: string) {
    setNotesPrivate(value);
    persistNotesDraft(session.id, {
      notesPrivate: value,
      updatedAt: new Date().toISOString(),
    });
  }

  async function substitute(item: SessionExercise) {
    const exerciseId = substitutes[item.id];
    if (!exerciseId) return;
    const { error } = await apiClient.POST("/sessions/{session_id}/exercises", {
      params: { path: { session_id: session.id } },
      body: { exercise_id: exerciseId, expected_version: session.version, replace_session_exercise_id: item.id, substitution_reason: "Member substitution" },
    });
    setMessage(error ? "Substitution could not be saved." : "Exercise substituted in this session only.");
    if (!error) await refresh();
  }

  async function addExercise() {
    if (!newExercise) return;
    const { error } = await apiClient.POST("/sessions/{session_id}/exercises", {
      params: { path: { session_id: session.id } },
      body: { exercise_id: newExercise, expected_version: session.version },
    });
    setMessage(error ? "Exercise could not be added." : "Exercise added.");
    if (!error) {
      setNewExercise("");
      await refresh();
    }
  }

  async function saveSession(status?: "in_progress" | "completed") {
    try {
      const { error } = await apiClient.PATCH("/sessions/{session_id}", {
        params: { path: { session_id: session.id } },
        body: {
          ...(status ? { status } : {}),
          notes_private: notesPrivate,
        },
      });
      if (error) throw new Error("Session write failed");
      persistNotesDraft(session.id, null);
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
          {session.status === "completed" ? <button className="button button--primary" onClick={() => void saveSession("in_progress")} type="button">Resume workout</button> : <button className="button button--primary" onClick={() => void saveSession("completed")} type="button">Complete workout</button>}
        </div>
        {message ? <p className="ink-status" role="status">{message}</p> : null}
      </div>

      <div className="journal-page journal-page--right">
        <ol className="journal-exercises">
          {session.exercises.map((item) => {
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
                {previousItem?.sets.at(-1) ? <p className="previous-performance">Previous: {setSummary(previousItem.sets.at(-1)!)}</p> : null}
                {item.sets.length && session.status !== "in_progress" ? <ul className="logged-sets">{item.sets.map((set) => <li key={set.id}><span>Set {set.sequence}</span><strong>{setSummary(set)}</strong><small>{set.set_type}</small></li>)}</ul> : null}
                {session.status === "in_progress" && catalogExercise ? <SetEntry item={item} measurement={catalogExercise.measurement_type} onSaved={refresh} sessionId={session.id} /> : null}
                {session.status === "in_progress" ? <div className="substitution-control"><label htmlFor={`substitute-${item.id}`}>Substitute exercise</label><select id={`substitute-${item.id}`} onChange={(event) => setSubstitutes({ ...substitutes, [item.id]: event.target.value })} value={substitutes[item.id] ?? ""}><option value="">Choose movement</option>{exercises.filter((exercise) => exercise.id !== item.exercise_id).map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select><button className="button" onClick={() => void substitute(item)} type="button">Substitute</button></div> : null}
              </li>
            );
          })}
        </ol>
        {session.status === "in_progress" ? <div className="add-exercise"><label htmlFor="add-exercise">Add exercise</label><select id="add-exercise" onChange={(event) => setNewExercise(event.target.value)} value={newExercise}><option value="">Choose movement</option>{exercises.map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select><button className="button" onClick={() => void addExercise()} type="button">Add</button></div> : null}
      </div>
    </section>
  );
}

export function JournalPage() {
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
      {selected && exercisesQuery.data ? <SessionBook exercises={exercisesQuery.data} key={selected.id} refresh={refresh} session={selected} sessions={sessions} /> : null}
    </article>
  );
}
