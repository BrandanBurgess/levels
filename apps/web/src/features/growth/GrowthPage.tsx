import type { components } from "@levels/api-client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink } from "react-router-dom";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import { formatRecordValue, type UnitPreference } from "../../utils/units";

type Suggestion = components["schemas"]["GrowthSuggestion"];

async function loadSuggestions(date?: string) {
  const { data, error } = await apiClient.GET("/growth/suggestions", {
    params: { query: { ...(date ? { date } : {}) } },
  });
  if (!data || error) throw new Error("Growth request failed");
  return data;
}

function actionLabel(suggestion: Suggestion, units: UnitPreference) {
  const delta = suggestion.suggested_delta;
  switch (suggestion.suggestion_type) {
    case "increase_load":
      return `Increase by ${formatRecordValue(delta ?? 0, suggestion.delta_unit ?? "kg", units)}`;
    case "add_rep":
      return "Add one rep";
    case "repeat_load":
      return "Repeat the load";
    case "maintain":
      return "Maintain today";
    case "reduce_volume":
      return "Reduce volume";
    case "easier_variation":
      return "Use an easier variation";
    case "no_progression":
      return "Pause progression";
    default:
      return "Build more history";
  }
}

function evidenceLabel(sourceId: string, index: number) {
  return `Session ${index + 1} · ${sourceId.slice(0, 8)}`;
}

export function GrowthPage() {
  const { isAuthenticated, user } = useAuth();
  const units = user?.preferred_units ?? "metric";
  const [date, setDate] = useState("");
  const [usedExercise, setUsedExercise] = useState<string>();
  const query = useQuery({
    queryKey: ["growth-suggestions", date],
    queryFn: () => loadSuggestions(date || undefined),
  });

  function acceptSuggestion(suggestion: Suggestion) {
    sessionStorage.setItem(
      `levels:growth:accepted:${suggestion.exercise_id}`,
      JSON.stringify({ suggestion, acceptedAt: new Date().toISOString() }),
    );
    setUsedExercise(suggestion.exercise_id);
  }

  return (
    <article className="page-shell growth-page">
      <header className="page-heading growth-heading">
        <div>
          <p className="eyebrow">EXPLAINABLE GUIDANCE</p>
          <h1>Growth</h1>
          <p>Small next steps grounded in recent sessions—not guarantees, scores, or max attempts.</p>
        </div>
        <label className="growth-date" htmlFor="growth-date">
          Training date
          <input id="growth-date" onChange={(event) => setDate(event.target.value)} type="date" value={date} />
        </label>
      </header>

      <aside className="growth-safety">
        <strong>How guidance works</strong>
        <span>Pain and poor recovery pause overload. Training guidance is not medical advice.</span>
      </aside>

      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <ErrorState message="Growth guidance could not be loaded." onRetry={() => void query.refetch()} /> : null}
      {query.data?.length === 0 ? <EmptyState title="No visible guidance">There is no scheduled training day or the owner has kept progress guidance private.</EmptyState> : null}

      {query.data ? (
        <div className="growth-grid">
          {query.data.map((suggestion) => (
            <section className={`growth-card growth-card--${suggestion.suggestion_type}`} key={suggestion.exercise_id}>
              <div className="growth-card__heading">
                <div><p className="card-label">{suggestion.confidence} confidence</p><h2>{suggestion.exercise_name}</h2></div>
                <span className={`confidence-dot confidence-dot--${suggestion.confidence}`} aria-label={`${suggestion.confidence} confidence`} />
              </div>
              <p className="growth-action">{actionLabel(suggestion, units)}</p>
              <div className="growth-reasoning">
                <h3>Why this suggestion</h3>
                <ul>{suggestion.explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul>
              </div>
              <div className="growth-evidence">
                <h3>Recent evidence</h3>
                {suggestion.source_session_ids.length ? <ol>{suggestion.source_session_ids.map((source, index) => <li key={source}>{evidenceLabel(source, index)}</li>)}</ol> : <p>No comparable sessions yet.</p>}
              </div>
              {isAuthenticated ? <div className="growth-card__actions"><button className="button button--primary" disabled={suggestion.suggestion_type === "insufficient_data"} onClick={() => acceptSuggestion(suggestion)} type="button">Use suggestion</button><NavLink className="button" to="/journal">Open Journal</NavLink>{usedExercise === suggestion.exercise_id ? <span role="status">Saved for the next workout.</span> : null}</div> : null}
            </section>
          ))}
        </div>
      ) : null}
    </article>
  );
}
