import type { components } from "@levels/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { apiClient } from "../../api/client";
import { ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";
import { AppearancePanel } from "./AppearancePanel";
import "./CharacterPage.css";

type Profile = components["schemas"]["Profile"];
type Settings = components["schemas"]["Settings"];
type Today = components["schemas"]["TodayV2"];

interface CharacterOverview {
  profile: Profile;
  settings: Settings;
  today: Today;
}

function moveCharacterTab(event: KeyboardEvent<HTMLButtonElement>) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const tabs = Array.from(event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? []);
  const currentIndex = tabs.indexOf(event.currentTarget);
  if (currentIndex < 0 || tabs.length === 0) return;
  event.preventDefault();
  const nextIndex = event.key === "Home"
    ? 0
    : event.key === "End"
      ? tabs.length - 1
      : (currentIndex + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
  tabs[nextIndex]?.focus();
  tabs[nextIndex]?.click();
}

async function fetchCharacterOverview(): Promise<CharacterOverview> {
  const [profileResult, settingsResult, todayResult] = await Promise.all([
    apiClient.GET("/me/profile"),
    apiClient.GET("/settings"),
    apiClient.GET("/today", { params: { query: {} } }),
  ]);
  if (!profileResult.data || profileResult.error || !settingsResult.data || settingsResult.error || !todayResult.data || todayResult.error) {
    throw new Error("Character request failed");
  }
  return { profile: profileResult.data, settings: settingsResult.data, today: todayResult.data };
}

function formatHeight(heightCm: number, units: Profile["preferred_units"]) {
  if (units === "metric") return `${heightCm} cm`;
  const totalInches = Math.round(heightCm / 2.54);
  return `${Math.floor(totalInches / 12)} ft ${totalInches % 12} in`;
}

function formatWeight(weightKg: number, units: Profile["preferred_units"]) {
  return units === "metric" ? `${weightKg.toFixed(1)} kg` : `${Math.round(weightKg * 2.20462)} lb`;
}

function ProfileEditor({ profile }: { profile: Profile }) {
  const queryClient = useQueryClient();
  const [height, setHeight] = useState(profile.height_cm ?? 179);
  const [weight, setWeight] = useState(profile.body_weight_kg ?? 79.4);
  const mutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.PATCH("/me/profile", {
        body: { height_cm: height, body_weight_kg: weight },
      });
      if (!data || error) throw new Error("Profile update failed");
      return data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<CharacterOverview>(["character-overview"], (current) =>
        current ? { ...current, profile: updated } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="character-editor" onSubmit={submit}>
      <div className="card-heading-row">
        <div>
          <p className="card-label">Private profile</p>
          <h2>Profile measurements</h2>
        </div>
        <span className="owner-pill">PRIVATE</span>
      </div>
      <p className="muted-copy">Measurements describe your profile; they never score or rank your body.</p>

      <div className="measurement-control">
        <label htmlFor="height-range">Height</label>
        <output htmlFor="height-range height-number">{height} cm</output>
        <input id="height-range" max="230" min="120" onChange={(event) => setHeight(Number(event.target.value))} step="1" type="range" value={height} />
        <input aria-label="Height in centimetres" id="height-number" max="230" min="120" onChange={(event) => setHeight(Number(event.target.value))} step="1" type="number" value={height} />
      </div>

      <div className="measurement-control">
        <label htmlFor="weight-range">Body weight</label>
        <output htmlFor="weight-range weight-number">{weight.toFixed(1)} kg</output>
        <input id="weight-range" max="250" min="35" onChange={(event) => setWeight(Number(event.target.value))} step="0.1" type="range" value={weight} />
        <input aria-label="Body weight in kilograms" id="weight-number" max="250" min="35" onChange={(event) => setWeight(Number(event.target.value))} step="0.1" type="number" value={weight} />
      </div>

      {mutation.isError ? <p className="form-error" role="alert">Profile changes could not be saved.</p> : null}
      {mutation.isSuccess ? <p className="form-success" role="status">Profile measurements saved.</p> : null}
      <button className="button button--primary" disabled={mutation.isPending} type="submit">
        {mutation.isPending ? "Saving…" : "Save measurements"}
      </button>
    </form>
  );
}

function CharacterOverviewPanel({ overview }: { overview: CharacterOverview }) {
  const queryClient = useQueryClient();
  const [view, setView] = useState<"front" | "back">("front");
  const [skipEffect, setSkipEffect] = useState<"advance" | "keep">("advance");
  const [skipMessage, setSkipMessage] = useState("");
  const [isSkipping, setIsSkipping] = useState(false);
  const { profile, settings, today } = overview;

  async function skipToday(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSkipping(true);
    setSkipMessage("");
    try {
      const result = await apiClient.POST("/today/skip", {
        params: { header: { "Idempotency-Key": crypto.randomUUID() } },
        body: {
          local_date: today.local_date,
          schedule_effect: skipEffect,
          expected_version: today.schedule_version,
        },
      });
      if (result.data) {
        queryClient.setQueryData<CharacterOverview>(["character-overview"], (current) =>
          current ? { ...current, today: result.data! } : current,
        );
        queryClient.setQueryData(["today"], result.data);
        setSkipMessage("Today skipped. Your plan and streak were updated.");
      } else if (result.response.status === 409) {
        setSkipMessage("Your schedule changed elsewhere. We refreshed the latest plan.");
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["character-overview"] }),
          queryClient.invalidateQueries({ queryKey: ["today"] }),
        ]);
      } else {
        setSkipMessage("Today could not be skipped. Try again.");
      }
    } catch {
      setSkipMessage("Today could not be skipped. Try again.");
    } finally {
      setIsSkipping(false);
    }
  }

  return (
    <div aria-labelledby="character-overview-tab" className="character-overview" id="character-overview-panel" role="tabpanel">
      <div className="character-layout">
        <section className="character-avatar-card" aria-labelledby="avatar-heading">
          <div className="card-heading-row">
            <div>
              <p className="card-label">Current development</p>
              <h2 id="avatar-heading">Today’s muscle map</h2>
            </div>
            <div aria-label="Avatar view" className="segmented-control" role="group">
              <button aria-pressed={view === "front"} onClick={() => setView("front")} type="button">Front</button>
              <button aria-pressed={view === "back"} onClick={() => setView("back")} type="button">Back</button>
            </div>
          </div>
          <Avatar
            appearance={today.avatar}
            auraTier={today.streak.tier}
            reducedMotion={settings.reduced_motion_override === true}
            targets={today.muscle_targets.map((target) => ({
              displayName: target.display_name,
              regionIds: target.svg_region_ids,
              role: target.role,
            }))}
            view={view}
          />
        </section>

        <aside className="character-profile-card" aria-labelledby="profile-facts-heading">
          <p className="card-label">Profile</p>
          <h2 id="profile-facts-heading">At a glance</h2>
          <dl className="character-facts">
            <div><dt>Name</dt><dd>{profile.display_name}</dd></div>
            <div><dt>Height</dt><dd>{profile.height_cm != null ? formatHeight(profile.height_cm, profile.preferred_units) : "Not set"}</dd></div>
            <div><dt>Body weight</dt><dd>{profile.body_weight_kg != null ? formatWeight(profile.body_weight_kg, profile.preferred_units) : "Not set"}</dd></div>
            <div><dt>Units</dt><dd>{profile.preferred_units}</dd></div>
            <div><dt>Current streak</dt><dd>{today.streak.current_count} · {today.streak.tier}</dd></div>
          </dl>
          <div className="character-workout-summary">
            <p className="card-label">Effective plan</p>
            <strong>{today.effective_day?.name ?? "Recovery day"}</strong>
            <span>{today.exercise_plan.length} planned exercises</span>
            <form className="character-skip" onSubmit={(event) => void skipToday(event)}>
              <p className="muted-copy">Skipping records a missed training opportunity and resets your current streak.</p>
              <label>
                After skipping
                <select
                  disabled={isSkipping}
                  onChange={(event) => setSkipEffect(event.target.value as "advance" | "keep")}
                  value={skipEffect}
                >
                  <option value="advance">Advance to the next workout</option>
                  <option value="keep">Keep this workout next</option>
                </select>
              </label>
              <button className="button button--quiet" disabled={isSkipping} type="submit">
                {isSkipping ? "Skipping…" : "Skip today"}
              </button>
            </form>
            {skipMessage ? <p aria-live="polite" className="character-skip__message">{skipMessage}</p> : null}
          </div>
          <p className="character-note">Built through consistent training. No ideals, comparisons, or body ratings.</p>
        </aside>
      </div>

      <ProfileEditor profile={profile} />
    </div>
  );
}

export function CharacterPage() {
  const [tab, setTab] = useState<"overview" | "appearance">("overview");
  const query = useQuery({ queryKey: ["character-overview"], queryFn: fetchCharacterOverview });

  return (
    <article className="page-shell character-page">
      <header className="page-heading">
        <p className="eyebrow">YOUR CHARACTER</p>
        <h1>{query.data?.profile.display_name ?? "Character"}</h1>
        <p>A neutral view of your training, today’s target muscles, and your chosen appearance.</p>
      </header>

      <div aria-label="Character sections" className="character-tabs" role="tablist">
        <button
          aria-controls="character-overview-panel"
          aria-selected={tab === "overview"}
          id="character-overview-tab"
          onClick={() => setTab("overview")}
          onKeyDown={moveCharacterTab}
          role="tab"
          tabIndex={tab === "overview" ? 0 : -1}
          type="button"
        >Overview</button>
        <button
          aria-controls="character-appearance-panel"
          aria-selected={tab === "appearance"}
          id="character-appearance-tab"
          onClick={() => setTab("appearance")}
          onKeyDown={moveCharacterTab}
          role="tab"
          tabIndex={tab === "appearance" ? 0 : -1}
          type="button"
        >Appearance</button>
      </div>

      {tab === "overview" ? (
        <>
          {query.isPending ? <LoadingState /> : null}
          {query.isError ? <ErrorState message="Character data could not be loaded." onRetry={() => void query.refetch()} /> : null}
          {query.data ? <CharacterOverviewPanel overview={query.data} /> : null}
        </>
      ) : (
        <div aria-labelledby="character-appearance-tab" id="character-appearance-panel" role="tabpanel">
          <AppearancePanel />
        </div>
      )}
    </article>
  );
}
