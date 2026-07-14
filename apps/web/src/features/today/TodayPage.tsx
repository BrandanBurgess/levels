import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { EmptyState, ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";

type Dashboard = components["schemas"]["PublicDashboard"];
type WaterDay = components["schemas"]["WaterDay"];
type Settings = components["schemas"]["Settings"];

async function fetchDashboard(): Promise<Dashboard> {
  const { data, error } = await apiClient.GET("/public/dashboard");
  if (error || !data) throw new Error("Dashboard request failed");
  return data;
}

async function fetchSettings(): Promise<Settings> {
  const { data, error } = await apiClient.GET("/settings");
  if (error || !data) throw new Error("Settings request failed");
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

function WaterControls({ quickAdds, water }: { quickAdds: number[]; water: WaterDay }) {
  const queryClient = useQueryClient();
  const [customAmount, setCustomAmount] = useState("375");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function publish(updated: WaterDay, successMessage: string) {
    queryClient.setQueryData<Dashboard>(["public-dashboard"], (current) =>
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
      setError(
        water.entries.length === 0
          ? "There is no water entry to undo."
          : "The latest water entry could not be undone.",
      );
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
        {quickAdds.map((amount) => (
          <button
            className="button water-quick-add__button"
            disabled={isSubmitting}
            key={amount}
            onClick={() => void addWater(amount, "quick_add")}
            type="button"
          >
            +{amount} mL
          </button>
        ))}
      </div>
      <form className="water-custom" onSubmit={submitCustom}>
        <label htmlFor="custom-water-amount">Custom amount</label>
        <div>
          <input
            disabled={isSubmitting}
            id="custom-water-amount"
            inputMode="numeric"
            max="5000"
            min="1"
            onChange={(event) => setCustomAmount(event.target.value)}
            step="1"
            type="number"
            value={customAmount}
          />
          <span>mL</span>
          <button className="button" disabled={isSubmitting} type="submit">Add</button>
        </div>
      </form>
      <button
        className="button button--quiet"
        disabled={isSubmitting || water.entries.length === 0}
        onClick={() => void undoWater()}
        type="button"
      >
        Undo latest
      </button>
      {message ? <p className="form-success" role="status">{message}</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </div>
  );
}

export function TodayPage() {
  const { isAuthenticated } = useAuth();
  const query = useQuery({ queryKey: ["public-dashboard"], queryFn: fetchDashboard });
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
    enabled: isAuthenticated,
  });
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
            {isAuthenticated && dashboard.water ? (
              <WaterControls
                quickAdds={settingsQuery.data?.water_quick_add_ml ?? [250, 500, 750]}
                water={dashboard.water}
              />
            ) : null}
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
