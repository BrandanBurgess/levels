import type { components, operations } from "@levels/api-client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";

type Exercise = components["schemas"]["Exercise"];
type ExerciseQuery = NonNullable<operations["listExercises"]["parameters"]["query"]>;

const muscleOptions = [
  ["upper_chest", "Upper Chest"], ["mid_chest", "Mid Chest"], ["front_delts", "Front Delts"],
  ["side_delts", "Side Delts"], ["rear_delts", "Rear Delts"], ["lats", "Lats"],
  ["upper_back", "Upper Back"], ["biceps", "Biceps"], ["triceps", "Triceps"],
  ["abs", "Abs"], ["glutes", "Glutes"], ["quads", "Quads"], ["hamstrings", "Hamstrings"],
] as const;

async function fetchExercises(query: ExerciseQuery): Promise<Exercise[]> {
  const { data, error } = await apiClient.GET("/exercises", { params: { query } });
  if (!data || error) throw new Error("Exercise request failed");
  return data;
}

export function LibraryPage() {
  const [search, setSearch] = useState("");
  const [primary, setPrimary] = useState("");
  const [secondary, setSecondary] = useState("");
  const [region, setRegion] = useState("");
  const [pattern, setPattern] = useState("");
  const [equipment, setEquipment] = useState("");
  const [laterality, setLaterality] = useState("");
  const [selectedId, setSelectedId] = useState<string>();
  const filters: ExerciseQuery = {
    ...(search.trim() ? { q: search.trim() } : {}),
    ...(primary ? { primary_muscle: primary } : {}),
    ...(secondary ? { secondary_muscle: secondary } : {}),
    ...(region ? { body_region: region } : {}),
    ...(pattern ? { movement_pattern: pattern } : {}),
    ...(equipment ? { equipment } : {}),
    ...(laterality ? { unilateral: laterality === "unilateral" } : {}),
  };
  const query = useQuery({
    queryKey: ["exercises", filters],
    queryFn: () => fetchExercises(filters),
  });
  const exercises = query.data ?? [];
  const selected = exercises.find((exercise) => exercise.id === selectedId) ?? exercises[0];
  const groups = Object.entries(
    exercises.reduce<Record<string, Exercise[]>>((result, exercise) => {
      (result[exercise.variation_group] ??= []).push(exercise);
      return result;
    }, {}),
  );

  return (
    <article className="page-shell library-page">
      <header className="page-heading">
        <p className="eyebrow">EXERCISE CATALOG</p>
        <h1>Library</h1>
        <p>Search movements, compare variations, and see exactly which avatar regions they train.</p>
      </header>

      <section aria-label="Exercise filters" className="library-filters">
        <label className="library-search">
          <span>Search names and aliases</span>
          <input onChange={(event) => setSearch(event.target.value)} placeholder="Try incline bench" type="search" value={search} />
        </label>
        <label><span>Primary muscle</span><select onChange={(event) => setPrimary(event.target.value)} value={primary}><option value="">Any</option>{muscleOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span>Secondary muscle</span><select onChange={(event) => setSecondary(event.target.value)} value={secondary}><option value="">Any</option>{muscleOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span>Body region</span><select onChange={(event) => setRegion(event.target.value)} value={region}><option value="">Any</option>{["chest", "shoulders", "back", "arms", "core", "hips", "legs", "calves", "full_body", "cardiovascular"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label><span>Movement</span><select onChange={(event) => setPattern(event.target.value)} value={pattern}><option value="">Any</option>{["horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull", "squat", "hinge", "lunge", "carry", "core", "conditioning"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
        <label><span>Equipment</span><select onChange={(event) => setEquipment(event.target.value)} value={equipment}><option value="">Any</option>{["barbell", "dumbbell", "cable", "machine", "bodyweight", "kettlebell", "cardio_machine"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
        <label><span>Laterality</span><select onChange={(event) => setLaterality(event.target.value)} value={laterality}><option value="">Any</option><option value="bilateral">Bilateral</option><option value="unilateral">Unilateral</option></select></label>
      </section>

      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <ErrorState message="The exercise library could not be loaded." onRetry={() => void query.refetch()} /> : null}
      {!query.isPending && !query.isError && exercises.length === 0 ? <EmptyState title="No movements match">Clear or broaden a filter to see more exercises.</EmptyState> : null}

      {exercises.length > 0 ? (
        <div className="library-layout">
          <section aria-label="Exercise results" className="variation-groups">
            <p className="result-count" role="status">{exercises.length} movements · {groups.length} variation groups</p>
            {groups.map(([group, variations]) => (
              <section className="variation-group" key={group}>
                <h2>{group.replaceAll("_", " ")}</h2>
                <div className="variation-grid">
                  {variations.map((exercise) => (
                    <button aria-pressed={selected?.id === exercise.id} className="exercise-card" key={exercise.id} onClick={() => setSelectedId(exercise.id)} type="button">
                      <strong>{exercise.name}</strong>
                      <span>{exercise.equipment.replaceAll("_", " ")} · {exercise.movement_pattern.replaceAll("_", " ")}</span>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </section>

          {selected ? (
            <aside className="exercise-detail" aria-labelledby="exercise-detail-heading">
              <p className="card-label">Movement detail</p>
              <h2 id="exercise-detail-heading">{selected.name}</h2>
              <Avatar targets={selected.muscle_targets.map((target) => ({ displayName: target.display_name, regionIds: target.svg_region_ids, role: target.role }))} view="front" />
              <dl className="exercise-facts"><div><dt>Equipment</dt><dd>{selected.equipment.replaceAll("_", " ")}</dd></div><div><dt>Pattern</dt><dd>{selected.movement_pattern.replaceAll("_", " ")}</dd></div><div><dt>Tracking</dt><dd>{selected.measurement_type.replaceAll("_", " ")}</dd></div></dl>
              <h3>Available variations</h3>
              <ul className="alternative-list">{(groups.find(([name]) => name === selected.variation_group)?.[1] ?? []).filter((exercise) => exercise.id !== selected.id).map((exercise) => <li key={exercise.id}>{exercise.name}</li>)}</ul>
            </aside>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
