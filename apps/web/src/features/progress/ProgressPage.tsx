import type { components } from "@levels/api-client";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";

type Exercise = components["schemas"]["Exercise"];
type RecordItem = components["schemas"]["PersonalRecord"];
type WorkoutSession = components["schemas"]["WorkoutSession"];
type Metric = RecordItem["record_type"];

const metricLabels: Record<Metric, string> = {
  max_load: "Max load",
  reps_at_load: "Reps at load",
  estimated_1rm: "Estimated 1RM",
  session_volume: "Session volume",
  duration: "Duration",
  distance: "Distance",
  rounds: "Rounds",
};

async function fetchProgress(owner: boolean) {
  const [current, history, exercises, sessions] = await Promise.all([
    apiClient.GET("/records", { params: { query: { current_only: true } } }),
    apiClient.GET("/records", { params: { query: { current_only: false } } }),
    apiClient.GET("/exercises", { params: { query: {} } }),
    apiClient.GET("/sessions", { params: { query: { public_only: !owner } } }),
  ]);
  if (!current.data || !history.data || !exercises.data || !sessions.data) {
    throw new Error("Progress request failed");
  }
  return {
    current: current.data,
    history: history.data,
    exercises: exercises.data,
    sessions: sessions.data,
  };
}

function recordValue(record: RecordItem) {
  const value = Number(record.value_numeric.toFixed(2));
  return `${value.toLocaleString()} ${record.unit}`;
}

function TrendChart({ metric, points }: { metric: Metric; points: RecordItem[] }) {
  const ordered = [...points].sort((a, b) => a.achieved_at.localeCompare(b.achieved_at));
  const values = ordered.map((point) => point.value_numeric);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const coordinates = ordered.map((point, index) => {
    const x = ordered.length === 1 ? 50 : 6 + (index / (ordered.length - 1)) * 88;
    const y = 88 - ((point.value_numeric - min) / spread) * 70;
    return `${x},${y}`;
  });
  const summary = ordered.length
    ? `${metricLabels[metric]} moved from ${recordValue(ordered[0]!)} to ${recordValue(ordered.at(-1)!)} across ${ordered.length} record points.`
    : `No ${metricLabels[metric].toLowerCase()} history is visible for these filters.`;

  return (
    <figure className="progress-chart">
      <figcaption>
        <span>{metricLabels[metric]}</span>
        <strong>{summary}</strong>
        {metric === "estimated_1rm" ? <small>Estimated from logged submaximal sets; this is not a measured max.</small> : null}
      </figcaption>
      {ordered.length ? (
        <svg aria-label={`${metricLabels[metric]} trend`} role="img" viewBox="0 0 100 100">
          <title>{summary}</title>
          <line x1="6" x2="94" y1="88" y2="88" />
          <polyline points={coordinates.join(" ")} />
          {coordinates.map((coordinate, index) => {
            const [cx, cy] = coordinate.split(",");
            return <circle cx={cx} cy={cy} key={ordered[index]!.id} r="2.5" />;
          })}
        </svg>
      ) : <div className="progress-chart__empty">More visible history will form this trend.</div>}
      {ordered.length ? <ol className="chart-values">{ordered.map((point) => <li key={point.id}><time dateTime={point.achieved_at}>{new Date(point.achieved_at).toLocaleDateString()}</time><span>{recordValue(point)}</span></li>)}</ol> : null}
    </figure>
  );
}

function ConsistencyCalendar({ sessions }: { sessions: WorkoutSession[] }) {
  const trained = new Set(sessions.filter((session) => session.status === "completed").map((session) => session.session_date_local));
  const end = new Date();
  const days = Array.from({ length: 28 }, (_, index) => {
    const day = new Date(end);
    day.setDate(end.getDate() - (27 - index));
    const date = day.toISOString().slice(0, 10);
    return { date, label: day.toLocaleDateString(undefined, { month: "short", day: "numeric" }), trained: trained.has(date) };
  });
  const count = days.filter((day) => day.trained).length;
  return (
    <section className="consistency-card" aria-labelledby="consistency-heading">
      <p className="card-label">Last 28 days</p>
      <h2 id="consistency-heading">Consistency</h2>
      <p>{count} training {count === 1 ? "day" : "days"} logged. Open days are simply part of the timeline.</p>
      <ol aria-label="28-day training calendar" className="consistency-grid">
        {days.map((day) => <li className={day.trained ? "is-trained" : ""} key={day.date}><time dateTime={day.date}><span>{day.label}</span><strong>{day.trained ? "Training logged" : "Open day"}</strong></time></li>)}
      </ol>
    </section>
  );
}

export function ProgressPage() {
  const { isAuthenticated } = useAuth();
  const [exerciseId, setExerciseId] = useState("");
  const [muscle, setMuscle] = useState("");
  const [day, setDay] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [metric, setMetric] = useState<Metric>("estimated_1rm");
  const query = useQuery({ queryKey: ["progress", isAuthenticated], queryFn: () => fetchProgress(isAuthenticated) });
  const data = query.data;

  const muscles = useMemo(() => {
    const targets = data?.exercises.flatMap((exercise) => exercise.muscle_targets) ?? [];
    return [...new Map(targets.map((target) => [target.slug, target.display_name])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [data]);
  const eligibleExercises = useMemo(() => new Set((data?.exercises ?? []).filter((exercise) => !muscle || exercise.muscle_targets.some((target) => target.slug === muscle)).map((exercise) => exercise.id)), [data, muscle]);
  const dateAllows = (iso: string) => (!dateFrom || iso.slice(0, 10) >= dateFrom) && (!dateTo || iso.slice(0, 10) <= dateTo);
  const recordAllows = (record: RecordItem) => (!exerciseId || record.exercise_id === exerciseId) && eligibleExercises.has(record.exercise_id) && dateAllows(record.achieved_at);
  const visibleCurrent = data?.current.filter(recordAllows) ?? [];
  const visibleHistory = data?.history.filter(recordAllows) ?? [];
  const visibleSessions = data?.sessions.filter((session) => (!day || session.title === day) && dateAllows(session.session_date_local) && (!exerciseId || session.exercises.some((exercise) => exercise.exercise_id === exerciseId)) && (!muscle || session.exercises.some((exercise) => eligibleExercises.has(exercise.exercise_id)))) ?? [];
  const days = [...new Set((data?.sessions ?? []).map((session) => session.title))].sort();
  const chartMetrics = [...new Set(visibleHistory.map((record) => record.record_type))];
  const activeMetric = chartMetrics.includes(metric) ? metric : chartMetrics[0] ?? metric;
  const repRanges = [
    { label: "1–5 reps", minimum: 1, maximum: 5 },
    { label: "6–8 reps", minimum: 6, maximum: 8 },
    { label: "9–12 reps", minimum: 9, maximum: 12 },
    { label: "13+ reps", minimum: 13, maximum: Number.POSITIVE_INFINITY },
  ].map((range) => ({
    ...range,
    best: visibleHistory
      .filter((record) => record.record_type === "max_load" && record.reps_context != null && record.reps_context >= range.minimum && record.reps_context <= range.maximum)
      .sort((a, b) => b.value_numeric - a.value_numeric)[0],
  })).filter((range) => range.best != null);

  return (
    <article className="page-shell progress-page">
      <header className="page-heading">
        <p className="eyebrow">TRAINING HISTORY</p>
        <h1>Progress</h1>
        <p>Records and trends from logged work, with estimates clearly labelled and every chart repeated as text.</p>
      </header>

      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <ErrorState message="Progress history could not be loaded." onRetry={() => void query.refetch()} /> : null}
      {data ? <>
        <section aria-label="Progress filters" className="progress-filters">
          <label><span>Exercise</span><select onChange={(event) => setExerciseId(event.target.value)} value={exerciseId}><option value="">All exercises</option>{data.exercises.map((exercise: Exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}</select></label>
          <label><span>Muscle</span><select onChange={(event) => setMuscle(event.target.value)} value={muscle}><option value="">All muscles</option>{muscles.map(([slug, label]) => <option key={slug} value={slug}>{label}</option>)}</select></label>
          <label><span>Training day</span><select onChange={(event) => setDay(event.target.value)} value={day}><option value="">All days</option>{days.map((name) => <option key={name}>{name}</option>)}</select></label>
          <label><span>From</span><input onChange={(event) => setDateFrom(event.target.value)} type="date" value={dateFrom} /></label>
          <label><span>To</span><input onChange={(event) => setDateTo(event.target.value)} type="date" value={dateTo} /></label>
        </section>

        <section className="record-section" aria-labelledby="records-heading">
          <div><p className="card-label">Current bests</p><h2 id="records-heading">Personal records</h2></div>
          {visibleCurrent.length ? <div className="record-grid">{visibleCurrent.map((record) => <article className="record-card" key={record.id}><span>{metricLabels[record.record_type]}</span><strong>{recordValue(record)}</strong><small>{record.exercise_name}</small>{record.record_type === "estimated_1rm" ? <em>Estimate, not a measured max</em> : null}</article>)}</div> : <EmptyState title="No visible records">No personal records match these filters, or the owner has kept them private.</EmptyState>}
          {repRanges.length ? <div className="rep-range-records"><h3>Best record-setting load by rep range</h3><dl>{repRanges.map((range) => <div key={range.label}><dt>{range.label}</dt><dd>{recordValue(range.best!)}</dd></div>)}</dl></div> : null}
        </section>

        {visibleHistory.length ? <section className="trend-section" aria-labelledby="trend-heading"><div className="trend-heading"><div><p className="card-label">Historical improvements</p><h2 id="trend-heading">Trend</h2></div><label><span>Metric</span><select onChange={(event) => setMetric(event.target.value as Metric)} value={activeMetric}>{chartMetrics.map((item) => <option key={item} value={item}>{metricLabels[item]}</option>)}</select></label></div><TrendChart metric={activeMetric} points={visibleHistory.filter((record) => record.record_type === activeMetric)} /></section> : null}
        {data.history.length ? <ConsistencyCalendar sessions={visibleSessions} /> : null}

        <section className="history-card" aria-labelledby="history-heading"><p className="card-label">Visible sessions</p><h2 id="history-heading">Exercise history</h2>{visibleSessions.length ? <ol>{visibleSessions.map((session) => <li key={session.id}><time dateTime={session.session_date_local}>{new Date(`${session.session_date_local}T12:00:00`).toLocaleDateString()}</time><strong>{session.title}</strong><span>{session.exercises.length ? `${session.exercises.length} exercises` : "Summary shared"}</span></li>)}</ol> : <p>No visible sessions match these filters.</p>}</section>
      </> : null}
    </article>
  );
}
