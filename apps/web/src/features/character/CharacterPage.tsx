import type { components } from "@levels/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { useAuth } from "../../auth/context";
import { ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar } from "../avatar/Avatar";

type Dashboard = components["schemas"]["PublicDashboard"];
type PublicProfile = components["schemas"]["PublicProfile"];

async function fetchDashboard(): Promise<Dashboard> {
  const { data, error } = await apiClient.GET("/public/dashboard");
  if (!data || error) throw new Error("Character request failed");
  return data;
}

function formatHeight(heightCm: number, units: PublicProfile["preferred_units"]) {
  if (units === "metric") return `${heightCm} cm`;
  const totalInches = Math.round(heightCm / 2.54);
  return `${Math.floor(totalInches / 12)} ft ${totalInches % 12} in`;
}

function formatWeight(weightKg: number, units: PublicProfile["preferred_units"]) {
  return units === "metric" ? `${weightKg.toFixed(1)} kg` : `${Math.round(weightKg * 2.20462)} lb`;
}

function ProfileEditor({ profile }: { profile: PublicProfile }) {
  const queryClient = useQueryClient();
  const [height, setHeight] = useState(profile.height_cm ?? 179);
  const [weight, setWeight] = useState(profile.body_weight_kg ?? 79.4);
  const mutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.PATCH("/profile", {
        body: { height_cm: height, body_weight_kg: weight },
      });
      if (!data || error) throw new Error("Profile update failed");
      return data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<Dashboard>(["public-dashboard"], (current) =>
        current ? { ...current, profile: updated } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["public-profile"] });
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
          <p className="card-label">Owner controls</p>
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

export function CharacterPage() {
  const { isAuthenticated } = useAuth();
  const [view, setView] = useState<"front" | "back">("front");
  const query = useQuery({ queryKey: ["public-dashboard"], queryFn: fetchDashboard });
  const dashboard = query.data;

  return (
    <article className="page-shell character-page">
      <header className="page-heading">
        <p className="eyebrow">YOUR CHARACTER</p>
        <h1>{dashboard?.profile.display_name ?? "Character"}</h1>
        <p>A neutral view of the person behind the work and the muscles today’s plan develops.</p>
      </header>

      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <ErrorState message="Character data could not be loaded." onRetry={() => void query.refetch()} /> : null}

      {dashboard ? (
        <>
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
                targets={dashboard.muscle_targets.map((target) => ({
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
                <div><dt>Name</dt><dd>{dashboard.profile.display_name}</dd></div>
                <div><dt>Height</dt><dd>{dashboard.profile.height_cm != null ? formatHeight(dashboard.profile.height_cm, dashboard.profile.preferred_units) : "Private"}</dd></div>
                <div><dt>Body weight</dt><dd>{dashboard.profile.body_weight_kg != null ? formatWeight(dashboard.profile.body_weight_kg, dashboard.profile.preferred_units) : "Private"}</dd></div>
                <div><dt>Units</dt><dd>{dashboard.profile.preferred_units}</dd></div>
              </dl>
              <p className="character-note">Built through consistent training. No ideals, comparisons, or body ratings.</p>
            </aside>
          </div>

          {isAuthenticated ? <ProfileEditor profile={dashboard.profile} /> : null}
        </>
      ) : null}
    </article>
  );
}
