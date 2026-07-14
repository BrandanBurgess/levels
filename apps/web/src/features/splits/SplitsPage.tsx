import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";

type Split = components["schemas"]["Split"];
type EditableItem = Omit<components["schemas"]["TemplateItem"], "id"> & { id?: string };
type EditableDay = Omit<components["schemas"]["SplitDay"], "id" | "items"> & { id?: string; items: EditableItem[] };
type EditableSplit = Omit<Split, "days"> & { days: EditableDay[] };

async function loadSplits() {
  const { data, error } = await apiClient.GET("/splits");
  if (!data || error) throw new Error("Split request failed");
  return data;
}

async function loadExercises() {
  const { data, error } = await apiClient.GET("/exercises");
  if (!data || error) throw new Error("Exercise request failed");
  return data;
}

function resequence<T extends { sequence: number }>(values: T[]) {
  return values.map((value, index) => ({ ...value, sequence: index + 1 }));
}

function move<T extends { sequence: number }>(values: T[], index: number, direction: -1 | 1) {
  const destination = index + direction;
  if (destination < 0 || destination >= values.length) return values;
  const result = [...values];
  [result[index], result[destination]] = [result[destination]!, result[index]!];
  return resequence(result);
}

function toWrite(split: EditableSplit) {
  return {
    name: split.name,
    slug: split.slug,
    ...(split.description !== undefined ? { description: split.description } : {}),
    days: split.days.map((day) => ({
      ...(day.id ? { id: day.id } : {}),
      name: day.name,
      day_type: day.day_type,
      sequence: day.sequence,
      is_optional: day.is_optional,
      items: day.items.map((item) => ({
        ...(item.id ? { id: item.id } : {}),
        exercise_id: item.exercise.id,
        sequence: item.sequence,
        item_type: item.item_type,
        sets: item.sets,
        rep_min: item.rep_min ?? null,
        rep_max: item.rep_max ?? null,
        rest_seconds: item.rest_seconds ?? null,
        target_rir: item.target_rir ?? null,
        optional: item.optional,
        alternative_exercise_ids: item.alternatives?.map((alternative) => alternative.id) ?? [],
      })),
    })),
  };
}

export function SplitsPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const splitsQuery = useQuery({ queryKey: ["splits"], queryFn: loadSplits });
  const exercisesQuery = useQuery({ queryKey: ["exercises", "split-editor"], queryFn: loadExercises, enabled: isAuthenticated });
  const [selectedId, setSelectedId] = useState<string>();
  const [draft, setDraft] = useState<EditableSplit>();
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string>();
  const selected = draft ?? splitsQuery.data?.find((split) => split.id === selectedId) ?? splitsQuery.data?.[0];

  function selectSplit(split: Split) {
    setSelectedId(split.id);
    setDraft(undefined);
    setMessage(undefined);
  }

  function edit(mutator: (value: EditableSplit) => EditableSplit) {
    if (selected) setDraft(mutator(structuredClone(selected)));
  }

  async function save() {
    if (!selected) return;
    setSaving(true);
    setMessage(undefined);
    const { data, error } = await apiClient.PATCH("/splits/{split_id}", {
      params: { path: { split_id: selected.id } },
      body: toWrite(selected),
    });
    setSaving(false);
    if (!data || error) return setMessage("Split changes could not be saved.");
    setDraft(undefined);
    setSelectedId(data.id);
    setMessage("Split changes saved.");
    await queryClient.invalidateQueries({ queryKey: ["splits"] });
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    const slug = newName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const { data } = await apiClient.POST("/splits", { body: { name: newName, slug, days: [] } });
    if (data) {
      setNewName("");
      setSelectedId(data.id);
      await queryClient.invalidateQueries({ queryKey: ["splits"] });
    }
  }

  async function activate() {
    if (!selected) return;
    await apiClient.POST("/splits/{split_id}/activate", { params: { path: { split_id: selected.id } } });
    await queryClient.invalidateQueries({ queryKey: ["splits"] });
  }

  return (
    <article className="page-shell splits-page">
      <header className="page-heading"><p className="eyebrow">TRAINING PLAN</p><h1>Splits</h1><p>Explore every day, movement, and alternative before training.</p></header>
      {splitsQuery.isPending ? <LoadingState /> : null}
      {splitsQuery.isError ? <ErrorState message="Training splits could not be loaded." onRetry={() => void splitsQuery.refetch()} /> : null}
      {splitsQuery.data ? (
        <div className="splits-layout">
          <aside className="split-picker" aria-label="Available splits">
            {splitsQuery.data.map((split) => <button aria-pressed={selected?.id === split.id} key={split.id} onClick={() => selectSplit(split)} type="button"><strong>{split.name}</strong><span>{split.is_active ? "Active plan" : `${split.days.length} days`}</span></button>)}
            {isAuthenticated ? <form className="new-split" onSubmit={create}><label htmlFor="new-split-name">New split</label><input id="new-split-name" onChange={(event) => setNewName(event.target.value)} required value={newName} /><button className="button" type="submit">Create</button></form> : null}
          </aside>

          {selected ? <section className="split-detail" aria-labelledby="split-name">
            <div className="card-heading-row"><div><p className="card-label">{selected.is_active ? "Active split" : "Available plan"}</p><h2 id="split-name">{selected.name}</h2><p>{selected.description}</p></div>{isAuthenticated && !selected.is_active ? <button className="button" onClick={activate} type="button">Make active</button> : null}</div>
            {selected.days.length === 0 ? <EmptyState title="No days yet">Add the first training day with owner controls.</EmptyState> : null}
            <div className="split-days">{selected.days.map((day, dayIndex) => <section className="split-day" key={day.id ?? `new-day-${dayIndex}`}><div className="card-heading-row"><div><p className="card-label">Day {day.sequence}{day.is_optional ? " · Optional" : ""}</p><h3>{day.name}</h3></div>{isAuthenticated ? <div className="reorder-controls"><button aria-label={`Move ${day.name} up`} disabled={dayIndex === 0} onClick={() => edit((value) => ({ ...value, days: move(value.days, dayIndex, -1) }))} type="button">↑</button><button aria-label={`Move ${day.name} down`} disabled={dayIndex === selected.days.length - 1} onClick={() => edit((value) => ({ ...value, days: move(value.days, dayIndex, 1) }))} type="button">↓</button></div> : null}</div>
              <ol className="template-items">{day.items.map((item, itemIndex) => <li key={item.id ?? `new-item-${itemIndex}`}><div><strong>{item.exercise.name}</strong><span>{item.sets} sets · {item.item_type}</span>{item.alternatives?.length ? <small>Alternatives: {item.alternatives.map((alternative) => alternative.name).join(", ")}</small> : null}</div>{isAuthenticated ? <div className="reorder-controls"><button aria-label={`Move ${item.exercise.name} up`} disabled={itemIndex === 0} onClick={() => edit((value) => ({ ...value, days: value.days.map((candidate, index) => index === dayIndex ? { ...candidate, items: move(candidate.items, itemIndex, -1) } : candidate) }))} type="button">↑</button><button aria-label={`Move ${item.exercise.name} down`} disabled={itemIndex === day.items.length - 1} onClick={() => edit((value) => ({ ...value, days: value.days.map((candidate, index) => index === dayIndex ? { ...candidate, items: move(candidate.items, itemIndex, 1) } : candidate) }))} type="button">↓</button></div> : null}</li>)}</ol>
              {isAuthenticated && exercisesQuery.data?.[0] ? <button className="button" onClick={() => { const exercise = exercisesQuery.data![0]!; edit((value) => ({ ...value, days: value.days.map((candidate, index) => index === dayIndex ? { ...candidate, items: [...candidate.items, { exercise, sequence: candidate.items.length + 1, item_type: "accessory", sets: 3, optional: false, alternatives: [] }] } : candidate) })); }} type="button">Add {exercisesQuery.data[0].name}</button> : null}
            </section>)}</div>
            {isAuthenticated ? <div className="split-editor-actions"><button className="button" onClick={() => edit((value) => ({ ...value, days: [...value.days, { name: `Day ${value.days.length + 1}`, day_type: "training", sequence: value.days.length + 1, is_optional: false, items: [] }] }))} type="button">Add day</button><button className="button button--primary" disabled={!draft || saving} onClick={save} type="button">{saving ? "Saving…" : "Save order"}</button>{message ? <p role="status">{message}</p> : null}</div> : null}
          </section> : null}
        </div>
      ) : null}
    </article>
  );
}
