import type { components } from "@levels/api-client";
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { apiClient } from "../../api/client";
import "./demo.css";

type DemoBootstrap = components["schemas"]["DemoBootstrap"];
type DemoSection = "today" | "character" | "splits" | "library" | "journal" | "progress";

const demoNavigation: Array<{ label: string; section: DemoSection; to: string }> = [
  { label: "Today", section: "today", to: "/demo" },
  { label: "Character", section: "character", to: "/demo/character" },
  { label: "Splits", section: "splits", to: "/demo/splits" },
  { label: "Library", section: "library", to: "/demo/library" },
  { label: "Journal", section: "journal", to: "/demo/journal" },
  { label: "Progress", section: "progress", to: "/demo/progress" },
];

async function loadDemo() {
  const { data, error } = await apiClient.GET("/demo/bootstrap");
  if (!data || error) throw new Error("Demo unavailable");
  return data;
}

function PersistentAction({ children, onAttempt }: { children: ReactNode; onAttempt: () => void }) {
  return <button className="demo-action" onClick={onAttempt} type="button">{children}</button>;
}

function DemoToday({ data, onAttempt }: { data: DemoBootstrap; onAttempt: () => void }) {
  const today = data.today;
  return (
    <div className="demo-content-grid">
      <section className="demo-card demo-card--hero">
        <p className="demo-kicker">{today.local_date}</p>
        <h2>{today.effective_day?.name ?? "Recovery day"}</h2>
        <p>{today.exercise_plan.length} planned movements · {today.muscle_targets.length} target groups</p>
        <PersistentAction onAttempt={onAttempt}>Start workout</PersistentAction>
      </section>
      <section className="demo-card">
        <p className="demo-kicker">Workout plan</p>
        <ol className="demo-plan-list">
          {today.exercise_plan.map((item) => <li key={item.id}><span>{item.exercise.name}</span><small>{item.planned_sets} sets</small></li>)}
        </ol>
      </section>
      <section className="demo-card">
        <p className="demo-kicker">Current streak</p>
        <strong className="demo-stat">{today.streak.current_count}</strong>
        <span className="demo-muted">{today.streak.tier} aura</span>
      </section>
      <section className="demo-card">
        <p className="demo-kicker">Hydration</p>
        <p className="demo-muted">Persistent updates are disabled in demo mode.</p>
        <PersistentAction onAttempt={onAttempt}>Add water</PersistentAction>
      </section>
    </div>
  );
}

function DemoCharacter({ data }: { data: DemoBootstrap }) {
  return <div className="demo-content-grid"><section className="demo-card demo-character-card"><div className="demo-silhouette" aria-hidden="true"><i /><i /></div><div><p className="demo-kicker">Character appearance</p><h2>{data.avatar.base_presentation === "female" ? "Female" : "Male"} base</h2><p className="demo-muted">{data.avatar.outfit_style.replaceAll("_", " ")} · {data.avatar.outfit_palette} palette</p></div></section><section className="demo-card"><p className="demo-kicker">Training aura</p><strong className="demo-stat">{data.streak.current_count}</strong><span className="demo-muted">session streak · {data.streak.tier}</span></section></div>;
}

function DemoSplits({ data }: { data: DemoBootstrap }) {
  return <div className="demo-list-grid">{data.splits.map((split) => <article className="demo-card" key={split.id}><p className="demo-kicker">{split.is_active ? "Active split" : "Saved split"}</p><h2>{split.name}</h2><p className="demo-muted">{split.days.length} training days</p></article>)}</div>;
}

function DemoLibrary({ data }: { data: DemoBootstrap }) {
  return <div className="demo-list-grid">{data.exercises.map((exercise) => <article className="demo-card" key={exercise.id}><p className="demo-kicker">{exercise.equipment}</p><h2>{exercise.name}</h2><p className="demo-muted">{exercise.movement_pattern} · {exercise.measurement_type.replaceAll("_", " ")}</p></article>)}</div>;
}

function DemoJournal({ data }: { data: DemoBootstrap }) {
  return <div className="demo-list-grid">{data.journal_samples.map((entry) => <article className="demo-card" key={entry.id}><p className="demo-kicker">{entry.session_date_local}</p><h2>{entry.title}</h2><p className="demo-muted">{entry.exercises_completed} exercises completed</p></article>)}</div>;
}

function DemoProgress({ data }: { data: DemoBootstrap }) {
  return <div className="demo-content-grid"><section className="demo-card"><p className="demo-kicker">Completed sessions</p><strong className="demo-stat">{data.progress.completed_sessions}</strong></section><section className="demo-card"><p className="demo-kicker">Current records</p><ol className="demo-plan-list">{data.progress.current_records.map((record) => <li key={record.id}><span>{record.exercise_name ?? "Exercise"}</span><small>{record.value_numeric} {record.unit}</small></li>)}</ol></section></div>;
}

function sectionFromPath(pathname: string): DemoSection {
  const candidate = pathname.split("/")[2];
  return demoNavigation.some((item) => item.section === candidate) ? candidate as DemoSection : "today";
}

export function DemoPage() {
  const location = useLocation();
  const [showPrompt, setShowPrompt] = useState(false);
  const query = useQuery({ queryKey: ["demo", "bootstrap"], queryFn: loadDemo });
  const section = sectionFromPath(location.pathname);

  return (
    <div className="demo-shell">
      <a className="skip-link" href="#demo-main">Skip to demo content</a>
      <header className="demo-header">
        <Link className="demo-brand" to="/" aria-label="LEVELS home"><span aria-hidden="true">L</span>LEVELS</Link>
        <p className="demo-badge">Demo — changes are not saved</p>
        <div className="demo-header__actions"><Link to="/login">Sign in</Link><Link className="demo-create-link" to="/register">Create account</Link></div>
      </header>
      <nav aria-label="Demo navigation" className="demo-nav">{demoNavigation.map((item) => <NavLink className={({ isActive }) => isActive ? "is-active" : undefined} end={item.to === "/demo"} key={item.to} to={item.to}>{item.label}</NavLink>)}</nav>
      <main className="demo-main" id="demo-main" tabIndex={-1}>
        <header className="demo-heading"><p className="demo-kicker">FICTIONAL TRAINING DATA</p><h1>{section === "today" ? `Today with ${query.data?.profile.display_name ?? "LEVELS"}` : section[0]!.toUpperCase() + section.slice(1)}</h1><p>Explore a realistic LEVELS account. This demo is isolated from member data and cannot save changes.</p></header>
        {query.isPending ? <p className="demo-state" role="status">Loading the demo…</p> : null}
        {query.isError ? <div className="demo-state" role="alert"><p>The demo is unavailable right now.</p><button onClick={() => void query.refetch()} type="button">Try again</button></div> : null}
        {query.data && section === "today" ? <DemoToday data={query.data} onAttempt={() => setShowPrompt(true)} /> : null}
        {query.data && section === "character" ? <DemoCharacter data={query.data} /> : null}
        {query.data && section === "splits" ? <DemoSplits data={query.data} /> : null}
        {query.data && section === "library" ? <DemoLibrary data={query.data} /> : null}
        {query.data && section === "journal" ? <DemoJournal data={query.data} /> : null}
        {query.data && section === "progress" ? <DemoProgress data={query.data} /> : null}
        {showPrompt ? <aside className="demo-save-prompt" aria-live="polite"><div><strong>Create an account to save changes.</strong><span>Your demo stays read-only.</span></div><Link to="/register">Create account</Link><button aria-label="Dismiss account prompt" onClick={() => setShowPrompt(false)} type="button">×</button></aside> : null}
      </main>
    </div>
  );
}
