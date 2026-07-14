import type { components } from "@levels/api-client";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";

type Dashboard = components["schemas"]["PublicDashboard"];

async function fetchDashboard(): Promise<Dashboard> {
  const { data, error } = await apiClient.GET("/public/dashboard");
  if (error || !data) throw new Error("Dashboard request failed");
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

export function TodayPage() {
  const query = useQuery({ queryKey: ["public-dashboard"], queryFn: fetchDashboard });
  const dashboard = query.data;
  const scheduledDay = dashboard?.scheduled_day;

  return (
    <article className="page-shell today-page">
      <header className="page-heading today-heading">
        <div>
          <p className="eyebrow">TODAY · {formatDate(dashboard?.date).toUpperCase()}</p>
          <h1>{scheduledDay ? `Ready for ${scheduledDay.name.split(" — ")[0]}` : "Ready for today"}</h1>
          <p>
            {dashboard
              ? `${dashboard.profile.display_name}'s current training plan and visible progress.`
              : "Your training plan and visible progress stay readable while the API wakes."}
          </p>
        </div>
        {dashboard ? <span className="level-badge">LEVEL 01</span> : null}
      </header>

      {query.isPending ? <LoadingState /> : null}
      {query.isError ? (
        <ErrorState
          message="Training data could not be loaded. Your public shell is still available."
          onRetry={() => void query.refetch()}
        />
      ) : null}

      {dashboard ? (
        <div className="today-grid">
          <section className="today-hero" aria-labelledby="target-heading">
            <div className="today-hero__aura" aria-hidden="true" />
            <Avatar targets={dashboard.muscle_targets.map((target) => ({
              displayName: target.display_name,
              regionIds: target.svg_region_ids,
              role: target.role,
            }))} />
            <div className="today-hero__content">
              <p className="card-label">Current focus</p>
              <h2 id="target-heading">Muscle targets</h2>
            </div>
          </section>

          <section className="today-card workout-plan" aria-labelledby="plan-heading">
            <div className="card-heading-row">
              <div>
                <p className="card-label">Scheduled workout</p>
                <h2 id="plan-heading">{scheduledDay?.name ?? "Recovery day"}</h2>
              </div>
              {scheduledDay ? <span className="item-count">{scheduledDay.items.length} moves</span> : null}
            </div>
            {scheduledDay ? (
              <ol className="exercise-list">
                {scheduledDay.items.map((item) => (
                  <li key={item.id}>
                    <span className="exercise-list__sequence">{item.sequence}</span>
                    <span className="exercise-list__name">
                      <strong>{item.exercise.name}</strong>
                      <small>
                        {item.sets} {item.sets === 1 ? "set" : "sets"}
                        {item.rep_min != null ? ` · ${item.rep_min}–${item.rep_max ?? item.rep_min} reps` : ""}
                      </small>
                    </span>
                    <span className={`exercise-list__type type-${item.item_type}`}>{item.item_type}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState title="No workout scheduled">
                Recovery supports the work. Browse the Library or review Progress when you’re ready.
              </EmptyState>
            )}
          </section>

          <section className="today-card compact-card" aria-labelledby="profile-heading">
            <p className="card-label">Character</p>
            <h2 id="profile-heading">{dashboard.profile.display_name}</h2>
            <dl className="profile-facts">
              <div><dt>Units</dt><dd>{dashboard.profile.preferred_units}</dd></div>
              {dashboard.profile.height_cm != null ? <div><dt>Height</dt><dd>{dashboard.profile.height_cm} cm</dd></div> : null}
              {dashboard.profile.body_weight_kg != null ? <div><dt>Weight</dt><dd>{dashboard.profile.body_weight_kg} kg</dd></div> : null}
            </dl>
          </section>

          <section className="today-card compact-card" aria-labelledby="water-heading">
            <p className="card-label">Hydration</p>
            <h2 id="water-heading">{dashboard.water ? `${dashboard.water.total_ml} mL` : "Private"}</h2>
            <p className="muted-copy">
              {dashboard.water
                ? `${Math.round(dashboard.water.progress_ratio * 100)}% of ${dashboard.water.goal_ml} mL goal`
                : "The owner has chosen not to publish water data."}
            </p>
          </section>

          <section className="today-card achievement-card" aria-labelledby="achievement-heading">
            <p className="card-label">Latest milestone</p>
            {dashboard.latest_achievements[0] ? (
              <>
                <h2 id="achievement-heading">{dashboard.latest_achievements[0].title}</h2>
                <p>{dashboard.latest_achievements[0].message}</p>
              </>
            ) : (
              <>
                <h2 id="achievement-heading">The next milestone starts here</h2>
                <p>Public achievements will appear after confirmed training records.</p>
              </>
            )}
          </section>
        </div>
      ) : null}
    </article>
  );
}
