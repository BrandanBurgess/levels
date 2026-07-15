import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";
import "./TodayPage.css";

type Today = components["schemas"]["TodayV2"];
type WaterDay = components["schemas"]["WaterDay"];
type Settings = components["schemas"]["Settings"];
type Split = components["schemas"]["Split"];
type Exercise = components["schemas"]["Exercise"];
type PlanItem = components["schemas"]["ExercisePlanItem"];
type PlanItemInput = components["schemas"]["ExercisePlanItemInput"];
type OverrideRequest = components["schemas"]["TodayOverrideRequest"];
type SkipEffect = components["schemas"]["SkipTodayRequest"]["schedule_effect"];

async function fetchToday(): Promise<Today> {
  const { data, error } = await apiClient.GET("/today", { params: { query: {} } });
  if (error || !data) throw new Error("Today request failed");
  return data;
}

async function fetchSettings(): Promise<Settings> {
  const { data, error } = await apiClient.GET("/settings");
  if (error || !data) throw new Error("Settings request failed");
  return data;
}

async function fetchSplits(): Promise<Split[]> {
  const { data, error } = await apiClient.GET("/splits");
  if (error || !data) throw new Error("Splits request failed");
  return data;
}

async function fetchExercises(): Promise<Exercise[]> {
  const { data, error } = await apiClient.GET("/exercises", { params: { query: {} } });
  if (error || !data) throw new Error("Exercises request failed");
  return data;
}

function formatDate(value?: string) {
  if (!value) return "Today";
  return new Intl.DateTimeFormat("en-CA", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function asPlanInput(item: PlanItem, sequence: number): PlanItemInput {
  return {
    source_template_item_id: item.source_template_item_id ?? null,
    exercise_id: item.exercise.id,
    sequence,
    item_type: item.item_type,
    planned_sets: item.planned_sets,
    rep_min: item.rep_min ?? null,
    rep_max: item.rep_max ?? null,
    duration_seconds: item.duration_seconds ?? null,
    distance_meters: item.distance_meters ?? null,
    rounds_target: item.rounds_target ?? null,
    rest_seconds: item.rest_seconds ?? null,
    target_rir: item.target_rir ?? null,
    superset_group: item.superset_group ?? null,
    optional: item.optional,
    notes: item.notes ?? null,
  };
}

function isConflict(response?: Response) {
  return response?.status === 409;
}

function WaterControls({ quickAdds, water }: { quickAdds: number[]; water: WaterDay }) {
  const queryClient = useQueryClient();
  const [customAmount, setCustomAmount] = useState("375");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function publish(updated: WaterDay, successMessage: string) {
    queryClient.setQueryData<Today>(["today"], (current) =>
      current ? { ...current, water: updated } : current,
    );
    setMessage(successMessage);
    setError("");
  }

  async function addWater(amountMl: number, source: "quick_add" | "custom") {
    setIsSubmitting(true);
    setMessage("");
    setError("");
    try {
      const { data, error: responseError } = await apiClient.POST("/water/today", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        body: { amount_ml: amountMl, source },
      });
      if (responseError || !data) throw new Error("Water update failed");
      publish(data, `${amountMl} mL added.`);
    } catch {
      setError("Hydration could not be updated. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function undoWater() {
    setIsSubmitting(true);
    setMessage("");
    setError("");
    try {
      const { data, error: responseError } = await apiClient.POST("/water/today/undo", {});
      if (responseError || !data) throw new Error("Water undo failed");
      publish(data, "Latest water entry undone.");
    } catch {
      setError(water.entries.length === 0 ? "There is no water entry to undo." : "The latest water entry could not be undone.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function submitCustom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = Number(customAmount);
    if (!Number.isInteger(amount) || amount < 1 || amount > 5000) {
      setMessage("");
      setError("Enter a whole number from 1 to 5000 mL.");
      return;
    }
    void addWater(amount, "custom");
  }

  return (
    <div className="water-controls" aria-label="Hydration controls">
      <div className="water-quick-add" aria-label="Quick add water">
        {quickAdds.map((amount) => <button className="button water-quick-add__button" disabled={isSubmitting} key={amount} onClick={() => void addWater(amount, "quick_add")} type="button">+{amount} mL</button>)}
      </div>
      <form className="water-custom" onSubmit={submitCustom}>
        <label htmlFor="custom-water-amount">Custom amount</label>
        <div><input disabled={isSubmitting} id="custom-water-amount" inputMode="numeric" max="5000" min="1" onChange={(event) => setCustomAmount(event.target.value)} step="1" type="number" value={customAmount} /><span>mL</span><button className="button" disabled={isSubmitting} type="submit">Add</button></div>
      </form>
      <button className="button button--quiet" disabled={isSubmitting || water.entries.length === 0} onClick={() => void undoWater()} type="button">Undo latest</button>
      {message ? <p className="form-success" role="status">{message}</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </div>
  );
}

function ScheduleActions({ splits, today }: { splits: Split[]; today: Today }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"closed" | "replace" | "skip">("closed");
  const [splitDayId, setSplitDayId] = useState("");
  const [effect, setEffect] = useState<"one_time" | "continue_from_here" | "swap_forward">("one_time");
  const [swapDate, setSwapDate] = useState("");
  const [skipEffect, setSkipEffect] = useState<SkipEffect>("advance");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const dayOptions = splits.flatMap((split) => split.days.map((day) => ({ ...day, splitName: split.name })));

  async function finish(result: Awaited<ReturnType<typeof apiClient.PUT>> | Awaited<ReturnType<typeof apiClient.POST>>, success: string) {
    if (result.data) {
      queryClient.setQueryData(["today"], result.data);
      setMessage(success);
      setMode("closed");
      return;
    }
    if (isConflict(result.response)) {
      setMessage("Your schedule changed elsewhere. We refreshed the latest plan; review it before trying again.");
      await queryClient.invalidateQueries({ queryKey: ["today"] });
      return;
    }
    setMessage("The schedule change could not be saved. Try again.");
  }

  async function changeWorkout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!splitDayId) return;
    setBusy(true);
    setMessage("");
    try {
      const body: OverrideRequest = effect === "swap_forward"
        ? { action: "swap", effective_split_day_id: splitDayId, expected_version: today.schedule_version, local_date: today.local_date, schedule_effect: "swap_forward", swap_target_local_date: swapDate }
        : { action: "replace", effective_split_day_id: splitDayId, expected_version: today.schedule_version, local_date: today.local_date, schedule_effect: effect };
      const result = await apiClient.PUT("/today/override", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        body,
      });
      await finish(result, effect === "one_time" ? "Today’s workout changed." : effect === "continue_from_here" ? "Workout changed and the schedule now continues from there." : "Today’s workout was swapped forward.");
    } catch {
      setMessage("The schedule change could not be saved. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function skip(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await apiClient.POST("/today/skip", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        body: { local_date: today.local_date, schedule_effect: skipEffect, expected_version: today.schedule_version },
      });
      await finish(result, skipEffect === "advance" ? "Today skipped. Your schedule advanced." : "Today skipped. Your next workout stays in place.");
    } catch {
      setMessage("The schedule change could not be saved. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="adapt-heading" className="today-card today-actions">
      <p className="card-label">Flexibility</p>
      <h2 id="adapt-heading">Adapt today</h2>
      <p>Change the plan without rewriting completed history.</p>
      <div className="today-actions__buttons">
        <button className="button" onClick={() => setMode(mode === "replace" ? "closed" : "replace")} type="button">Change workout</button>
        <button className="button button--quiet" onClick={() => setMode(mode === "skip" ? "closed" : "skip")} type="button">Skip today</button>
      </div>
      {mode === "replace" ? (
        <form className="today-action-form" onSubmit={(event) => void changeWorkout(event)}>
          <label>Workout<select aria-label="Replacement workout" onChange={(event) => setSplitDayId(event.target.value)} required value={splitDayId}><option value="">Choose a workout</option>{dayOptions.map((day) => <option key={day.id} value={day.id}>{day.splitName} · {day.name}</option>)}</select></label>
          <fieldset><legend>How should the schedule change?</legend>
            <label><input checked={effect === "one_time"} name="replacement-effect" onChange={() => setEffect("one_time")} type="radio" /> One time only</label>
            <label><input checked={effect === "continue_from_here"} name="replacement-effect" onChange={() => setEffect("continue_from_here")} type="radio" /> Continue from here</label>
            <label><input checked={effect === "swap_forward"} name="replacement-effect" onChange={() => setEffect("swap_forward")} type="radio" /> Swap forward</label>
          </fieldset>
          {effect === "swap_forward" ? <label>Swap with date<input aria-label="Swap target date" min={today.local_date} onChange={(event) => setSwapDate(event.target.value)} required type="date" value={swapDate} /></label> : null}
          <button className="button button--primary" disabled={busy} type="submit">{busy ? "Saving…" : "Apply workout change"}</button>
        </form>
      ) : null}
      {mode === "skip" ? (
        <form className="today-action-form" onSubmit={(event) => void skip(event)}>
          <p className="skip-streak-warning"><strong>Streak warning:</strong> Confirming a skip records a skipped training opportunity and resets your current {today.streak.current_count}-day streak.</p>
          <fieldset><legend>After skipping</legend>
            <label><input checked={skipEffect === "advance"} name="skip-effect" onChange={() => setSkipEffect("advance")} type="radio" /> Advance to the next workout</label>
            <label><input checked={skipEffect === "keep"} name="skip-effect" onChange={() => setSkipEffect("keep")} type="radio" /> Keep this workout next</label>
          </fieldset>
          <button className="button button--primary" disabled={busy} type="submit">{busy ? "Saving…" : "Confirm skip"}</button>
        </form>
      ) : null}
      {message ? <p className={message.includes("could not") || message.includes("elsewhere") ? "form-error" : "form-success"} role={message.includes("could not") || message.includes("elsewhere") ? "alert" : "status"}>{message}</p> : null}
    </section>
  );
}

type ExercisePickerScope = "recommended" | "all";
type ExerciseFilters = {
  equipment: string;
  measurement: string;
  movement: string;
  muscle: string;
};

const ITEM_TYPES: PlanItem["item_type"][] = ["activation", "power", "main", "accessory", "core", "conditioning"];

function nullableNumber(value: string) {
  return value === "" ? null : Number(value);
}

function sortedUnique(values: string[]) {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right));
}

function ExercisePlanEditor({ exercises, today }: { exercises: Exercise[]; today: Today }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<PlanItem[]>(today.exercise_plan);
  const [selectedExerciseId, setSelectedExerciseId] = useState(exercises[0]?.id ?? "");
  const [saveToSplit, setSaveToSplit] = useState(false);
  const [pickerScope, setPickerScope] = useState<ExercisePickerScope>("recommended");
  const [filters, setFilters] = useState<ExerciseFilters>({ equipment: "", measurement: "", movement: "", muscle: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const filterOptions = useMemo(() => ({
    equipment: sortedUnique(exercises.map((exercise) => exercise.equipment)),
    measurement: sortedUnique(exercises.map((exercise) => exercise.measurement_type)),
    movement: sortedUnique(exercises.map((exercise) => exercise.movement_pattern)),
    muscles: sortedUnique(exercises.flatMap((exercise) => exercise.muscle_targets.map((target) => target.slug))),
  }), [exercises]);
  const todayMuscles = useMemo(() => new Set(today.muscle_targets.map((target) => target.slug)), [today.muscle_targets]);
  const filteredExercises = useMemo(() => exercises.filter((exercise) =>
    (!filters.equipment || exercise.equipment === filters.equipment)
    && (!filters.measurement || exercise.measurement_type === filters.measurement)
    && (!filters.movement || exercise.movement_pattern === filters.movement)
    && (!filters.muscle || exercise.muscle_targets.some((target) => target.slug === filters.muscle)),
  ), [exercises, filters]);
  const addOptions = useMemo(() => {
    if (pickerScope === "all") return filteredExercises;
    const plannedMovements = new Set(draft.map((item) => item.exercise.movement_pattern));
    return filteredExercises.filter((exercise) =>
      plannedMovements.has(exercise.movement_pattern)
      || exercise.muscle_targets.some((target) => todayMuscles.has(target.slug)),
    );
  }, [draft, filteredExercises, pickerScope, todayMuscles]);

  useEffect(() => setDraft(today.exercise_plan), [today.exercise_plan]);
  useEffect(() => {
    if (!addOptions.some((exercise) => exercise.id === selectedExerciseId)) {
      setSelectedExerciseId(addOptions[0]?.id ?? "");
    }
  }, [addOptions, selectedExerciseId]);

  function resequence(items: PlanItem[]) {
    return items.map((item, index) => ({ ...item, sequence: index }));
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= draft.length) return;
    const next = [...draft];
    [next[index], next[target]] = [next[target]!, next[index]!];
    setDraft(resequence(next));
  }

  function add() {
    const exercise = addOptions.find((candidate) => candidate.id === selectedExerciseId);
    if (!exercise) return;
    setDraft((current) => [...current, {
      id: `draft-${crypto.randomUUID()}`,
      exercise,
      sequence: current.length,
      item_type: "accessory",
      planned_sets: 3,
      rep_min: exercise.default_rep_min ?? null,
      rep_max: exercise.default_rep_max ?? null,
      rest_seconds: exercise.default_rest_seconds ?? null,
      optional: false,
    }]);
  }

  function swap(index: number, exerciseId: string) {
    const exercise = exercises.find((candidate) => candidate.id === exerciseId);
    if (!exercise) return;
    setDraft((current) => current.map((item, itemIndex) => {
      if (itemIndex !== index) return item;
      const sameMeasurement = item.exercise.measurement_type === exercise.measurement_type;
      const usesReps = exercise.measurement_type === "load_reps" || exercise.measurement_type === "bodyweight_reps";
      return {
        ...item,
        exercise,
        source_template_item_id: null,
        rep_min: usesReps ? (sameMeasurement ? item.rep_min ?? null : exercise.default_rep_min ?? null) : null,
        rep_max: usesReps ? (sameMeasurement ? item.rep_max ?? null : exercise.default_rep_max ?? null) : null,
        duration_seconds: exercise.measurement_type === "duration" && sameMeasurement ? item.duration_seconds ?? null : null,
        distance_meters: exercise.measurement_type === "distance" && sameMeasurement ? item.distance_meters ?? null : null,
        rounds_target: exercise.measurement_type === "rounds" && sameMeasurement ? item.rounds_target ?? null : null,
      };
    }));
  }

  function updateItem(index: number, patch: Partial<PlanItem>) {
    setDraft((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function swapOptions(item: PlanItem) {
    const alternatives = filteredExercises.filter((exercise) => pickerScope === "all"
      || exercise.variation_group === item.exercise.variation_group
      || exercise.movement_pattern === item.exercise.movement_pattern
      || exercise.muscle_targets.some((target) => item.exercise.muscle_targets.some((currentTarget) => currentTarget.slug === target.slug)));
    return [item.exercise, ...alternatives.filter((exercise) => exercise.id !== item.exercise.id)];
  }

  function closeEditor() {
    setOpen(false);
    setSaveToSplit(false);
  }

  function openEditor() {
    setDraft(today.exercise_plan);
    setSaveToSplit(false);
    setPickerScope("recommended");
    setFilters({ equipment: "", measurement: "", movement: "", muscle: "" });
    setOpen(true);
    setMessage("");
  }

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const result = await apiClient.PUT("/today/exercises", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        body: {
          local_date: today.local_date,
          source_split_day_id: today.effective_day?.id ?? null,
          items: draft.map((item, index) => asPlanInput(item, index)),
          scope: saveToSplit ? "save_to_split" : "today_only",
          expected_version: today.schedule_version,
        },
      });
      if (result.data) {
        queryClient.setQueryData(["today"], result.data);
        setMessage(saveToSplit ? "Exercise plan saved to today and the split." : "Exercise plan saved for today only.");
        closeEditor();
      } else if (isConflict(result.response)) {
        setMessage("Your plan changed elsewhere. We refreshed the latest version; review it before saving again.");
        await queryClient.invalidateQueries({ queryKey: ["today"] });
      } else {
        setMessage("The exercise plan could not be saved. Try again.");
      }
    } catch {
      setMessage("The exercise plan could not be saved. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return <><button className="button" onClick={openEditor} type="button">Edit exercises</button>{message ? <p className="form-success" role="status">{message}</p> : null}</>;

  return (
    <div className="exercise-plan-editor">
      <fieldset className="exercise-picker-filters">
        <legend>Exercise picker</legend>
        <label>Collection<select aria-label="Exercise picker collection" onChange={(event) => setPickerScope(event.target.value as ExercisePickerScope)} value={pickerScope}><option value="recommended">Recommended alternatives</option><option value="all">All exercises</option></select></label>
        <label>Muscle<select aria-label="Muscle filter" onChange={(event) => setFilters((current) => ({ ...current, muscle: event.target.value }))} value={filters.muscle}><option value="">Any muscle</option>{filterOptions.muscles.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
        <label>Equipment<select aria-label="Equipment filter" onChange={(event) => setFilters((current) => ({ ...current, equipment: event.target.value }))} value={filters.equipment}><option value="">Any equipment</option>{filterOptions.equipment.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Movement<select aria-label="Movement filter" onChange={(event) => setFilters((current) => ({ ...current, movement: event.target.value }))} value={filters.movement}><option value="">Any movement</option>{filterOptions.movement.map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
        <label>Measurement<select aria-label="Measurement filter" onChange={(event) => setFilters((current) => ({ ...current, measurement: event.target.value }))} value={filters.measurement}><option value="">Any measurement</option>{filterOptions.measurement.map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
      </fieldset>
      <ol aria-label="Editable exercise plan">
        {draft.map((item, index) => (
          <li key={item.id}>
            <div className="exercise-plan-editor__item-heading"><strong>{item.exercise.name}</strong><div className="reorder-controls"><button aria-label={`Move ${item.exercise.name} up`} disabled={index === 0} onClick={() => move(index, -1)} type="button">↑</button><button aria-label={`Move ${item.exercise.name} down`} disabled={index === draft.length - 1} onClick={() => move(index, 1)} type="button">↓</button><button aria-label={`Remove ${item.exercise.name}`} onClick={() => setDraft((current) => resequence(current.filter((_, itemIndex) => itemIndex !== index)))} type="button">Remove</button></div></div>
            <label>Swap movement<select aria-label={`Swap ${item.exercise.name}`} onChange={(event) => swap(index, event.target.value)} value={item.exercise.id}>{swapOptions(item).map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select></label>
            <div className="prescription-grid">
              <label>Planned sets<input aria-label={`Planned sets for ${item.exercise.name}`} max="20" min="1" onChange={(event) => updateItem(index, { planned_sets: Number(event.target.value) })} required type="number" value={item.planned_sets} /></label>
              <label>Item type<select aria-label={`Item type for ${item.exercise.name}`} onChange={(event) => updateItem(index, { item_type: event.target.value as PlanItem["item_type"] })} value={item.item_type}>{ITEM_TYPES.map((value) => <option key={value}>{value}</option>)}</select></label>
              {(item.exercise.measurement_type === "load_reps" || item.exercise.measurement_type === "bodyweight_reps") ? <><label>Minimum reps<input aria-label={`Minimum reps for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { rep_min: nullableNumber(event.target.value) })} type="number" value={item.rep_min ?? ""} /></label><label>Maximum reps<input aria-label={`Maximum reps for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { rep_max: nullableNumber(event.target.value) })} type="number" value={item.rep_max ?? ""} /></label></> : null}
              {item.exercise.measurement_type === "duration" ? <label>Duration seconds<input aria-label={`Duration seconds for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { duration_seconds: nullableNumber(event.target.value) })} type="number" value={item.duration_seconds ?? ""} /></label> : null}
              {item.exercise.measurement_type === "distance" ? <label>Distance metres<input aria-label={`Distance metres for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { distance_meters: nullableNumber(event.target.value) })} step="any" type="number" value={item.distance_meters ?? ""} /></label> : null}
              {item.exercise.measurement_type === "rounds" ? <label>Target rounds<input aria-label={`Target rounds for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { rounds_target: nullableNumber(event.target.value) })} type="number" value={item.rounds_target ?? ""} /></label> : null}
              <label>Rest seconds<input aria-label={`Rest seconds for ${item.exercise.name}`} min="0" onChange={(event) => updateItem(index, { rest_seconds: nullableNumber(event.target.value) })} type="number" value={item.rest_seconds ?? ""} /></label>
              <label>Target RIR<input aria-label={`Target RIR for ${item.exercise.name}`} max="10" min="0" onChange={(event) => updateItem(index, { target_rir: nullableNumber(event.target.value) })} step="0.5" type="number" value={item.target_rir ?? ""} /></label>
              <label className="prescription-optional"><input aria-label={`Optional ${item.exercise.name}`} checked={item.optional} onChange={(event) => updateItem(index, { optional: event.target.checked })} type="checkbox" /> Optional exercise</label>
              <label className="prescription-notes">Notes<textarea aria-label={`Notes for ${item.exercise.name}`} maxLength={500} onChange={(event) => updateItem(index, { notes: event.target.value || null })} rows={2} value={item.notes ?? ""} /></label>
            </div>
          </li>
        ))}
      </ol>
      <div className="exercise-plan-editor__add"><label>Add movement<select aria-label="Exercise to add" disabled={addOptions.length === 0} onChange={(event) => setSelectedExerciseId(event.target.value)} value={selectedExerciseId}>{addOptions.length === 0 ? <option value="">No exercises match these filters</option> : addOptions.map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select></label><button className="button" disabled={!selectedExerciseId} onClick={add} type="button">Add exercise</button></div>
      <label className="save-scope"><input checked={saveToSplit} disabled={!today.effective_day} onChange={(event) => setSaveToSplit(event.target.checked)} type="checkbox" /> Save these changes to the split too</label>
      <div className="exercise-plan-editor__actions"><button className="button button--quiet" onClick={closeEditor} type="button">Cancel</button><button className="button button--primary" disabled={busy || draft.length === 0} onClick={() => void save()} type="button">{busy ? "Saving…" : saveToSplit ? "Save today and split" : "Save for today only"}</button></div>
      {message ? <p className="form-error" role="alert">{message}</p> : null}
    </div>
  );
}

export function TodayPage() {
  const query = useQuery({ queryKey: ["today"], queryFn: fetchToday });
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: fetchSettings });
  const splitsQuery = useQuery({ queryKey: ["splits"], queryFn: fetchSplits });
  const exercisesQuery = useQuery({ queryKey: ["exercises", "today-editor"], queryFn: fetchExercises });
  const today = query.data;
  const effectiveDay = today?.effective_day;

  return (
    <article className="page-shell today-page">
      <header className="page-heading today-heading"><div><p className="eyebrow">TODAY · {formatDate(today?.local_date).toUpperCase()}</p><h1>{effectiveDay ? `Ready for ${effectiveDay.name.split(" — ")[0]}` : "Ready for today"}</h1><p>{today ? `${today.user.display_name}, this plan can flex without losing your place.` : "Your private training plan is loading."}</p></div>{today ? <span className="level-badge">{today.streak.current_count} DAY STREAK</span> : null}</header>
      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <ErrorState message="Training data could not be loaded." onRetry={() => void query.refetch()} /> : null}
      {today ? (
        <div className="today-grid">
          <section className="today-hero" aria-labelledby="target-heading"><Avatar appearance={today.avatar} auraTier={today.streak.tier} reducedMotion={settingsQuery.data?.reduced_motion_override === true} targets={today.muscle_targets.map((target) => ({ displayName: target.display_name, regionIds: target.svg_region_ids, role: target.role }))} /><div className="today-hero__content"><p className="card-label">Current focus</p><h2 id="target-heading">Muscle targets</h2></div></section>
          <section className="today-card workout-plan" aria-labelledby="plan-heading"><div className="card-heading-row"><div><p className="card-label">Effective workout</p><h2 id="plan-heading">{effectiveDay?.name ?? "Recovery day"}</h2>{today.override ? <p className="today-override-note">Adjusted today · {today.override.schedule_effect.replaceAll("_", " ")}</p> : null}</div><span className="item-count">{today.exercise_plan.length} moves</span></div>
            {today.exercise_plan.length ? <ol className="exercise-list">{today.exercise_plan.map((item) => <li key={item.id}><span className="exercise-list__sequence">{item.sequence + 1}</span><span className="exercise-list__name"><strong>{item.exercise.name}</strong><small>{item.planned_sets} {item.planned_sets === 1 ? "set" : "sets"}{item.rep_min != null ? ` · ${item.rep_min}–${item.rep_max ?? item.rep_min} reps` : ""}</small></span><span className={`exercise-list__type type-${item.item_type}`}>{item.item_type}</span></li>)}</ol> : <EmptyState title="No workout scheduled">Recovery supports the work.</EmptyState>}
            {exercisesQuery.data ? <ExercisePlanEditor exercises={exercisesQuery.data} today={today} /> : null}
          </section>
          {splitsQuery.data ? <ScheduleActions splits={splitsQuery.data} today={today} /> : null}
          <section className="today-card compact-card" aria-labelledby="water-heading"><p className="card-label">Hydration</p><h2 id="water-heading">{today.water.total_ml} mL</h2><p className="muted-copy">{Math.round(today.water.progress_ratio * 100)}% of {today.water.goal_ml} mL goal</p><WaterControls quickAdds={settingsQuery.data?.water_quick_add_ml ?? [250, 500, 750]} water={today.water} /></section>
          <section className="today-card achievement-card" aria-labelledby="achievement-heading"><p className="card-label">Latest milestone</p>{today.latest_achievements[0] ? <><h2 id="achievement-heading">{today.latest_achievements[0].title}</h2><p>{today.latest_achievements[0].message}</p></> : <><h2 id="achievement-heading">The next milestone starts here</h2><p>Confirmed training records build progress over time.</p></>}</section>
        </div>
      ) : null}
    </article>
  );
}
