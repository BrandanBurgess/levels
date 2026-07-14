import type { components } from "@levels/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { downloadExport } from "../../api/export";
import { applyMotionPreference } from "../../app/motionPreference";
import { useAuth } from "../../auth/context";
import { ErrorState, LoadingState } from "../../ui/AsyncState";

type Profile = components["schemas"]["AdminProfile"];
type Settings = components["schemas"]["Settings"];
type Split = components["schemas"]["Split"];
type Visibility = components["schemas"]["Visibility"];
type VisibilityKey = keyof Visibility;

const visibilityOptions: { key: VisibilityKey; label: string; hint: string }[] = [
  { key: "show_height", label: "Height", hint: "Show height on the public profile." },
  { key: "show_body_weight", label: "Body weight", hint: "Show the latest profile weight." },
  { key: "show_water", label: "Hydration", hint: "Show today's total and goal progress." },
  { key: "show_session_summaries", label: "Workout summaries", hint: "Publish completed session summaries." },
  { key: "show_set_details", label: "Set details", hint: "Include individual set performance." },
  { key: "show_public_notes", label: "Public notes", hint: "Include notes explicitly written for visitors." },
  { key: "show_progress_charts", label: "Progress charts", hint: "Show training trend charts." },
  { key: "show_personal_records", label: "Personal records", hint: "Show confirmed records and milestones." },
  { key: "show_readiness", label: "Readiness", hint: "Show readiness when that feature has data." },
];

async function loadSettingsPage(): Promise<{ profile: Profile; settings: Settings; splits: Split[] }> {
  const [profile, settings, splits] = await Promise.all([
    apiClient.GET("/profile"),
    apiClient.GET("/settings"),
    apiClient.GET("/splits"),
  ]);
  if (!profile.data || profile.error || !settings.data || settings.error || !splits.data || splits.error) {
    throw new Error("Settings request failed");
  }
  return { profile: profile.data, settings: settings.data, splits: splits.data };
}

function SettingsForm({ profile, settings, splits }: { profile: Profile; settings: Settings; splits: Split[] }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [displayName, setDisplayName] = useState(profile.display_name);
  const [height, setHeight] = useState(profile.height_cm?.toString() ?? "");
  const [bodyWeight, setBodyWeight] = useState(profile.body_weight_kg?.toString() ?? "");
  const [preferredUnits, setPreferredUnits] = useState(profile.preferred_units);
  const [timezone, setTimezone] = useState(profile.timezone);
  const [activeSplitId, setActiveSplitId] = useState(settings.active_split_id ?? "");
  const [weekStartsOn, setWeekStartsOn] = useState(settings.week_starts_on);
  const [waterGoal, setWaterGoal] = useState(settings.default_water_goal_ml.toString());
  const [quickAdds, setQuickAdds] = useState(settings.water_quick_add_ml.join(", "));
  const [targetRir, setTargetRir] = useState((settings.default_target_rir ?? 2).toString());
  const [loadIncrement, setLoadIncrement] = useState((settings.default_load_increment_kg ?? 2.5).toString());
  const [motion, setMotion] = useState<"system" | "reduce" | "full">(
    settings.reduced_motion_override === null
      ? "system"
      : settings.reduced_motion_override
        ? "reduce"
        : "full",
  );
  const [visibility, setVisibility] = useState<Visibility>(settings.visibility);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportState, setExportState] = useState<"idle" | "working" | "success" | "error">("idle");

  function toggleVisibility(key: VisibilityKey, checked: boolean) {
    setVisibility((current) => ({ ...current, [key]: checked }));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedQuickAdds = quickAdds
      .split(",")
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value));
    if (
      !parsedQuickAdds.length
      || parsedQuickAdds.length > 6
      || parsedQuickAdds.some((value) => !Number.isInteger(value) || value < 1 || value > 5000)
    ) {
      setMessage("");
      setError("Enter one to six whole-number quick-add amounts from 1 to 5000 mL.");
      return;
    }

    setIsSaving(true);
    setMessage("");
    setError("");
    const reducedMotion = motion === "system" ? null : motion === "reduce";
    try {
      const [profileResult, settingsResult] = await Promise.all([
        apiClient.PATCH("/profile", {
          body: {
            display_name: displayName,
            height_cm: height === "" ? null : Number(height),
            body_weight_kg: bodyWeight === "" ? null : Number(bodyWeight),
            preferred_units: preferredUnits,
            timezone,
          },
        }),
        apiClient.PATCH("/settings", {
          body: {
            active_split_id: activeSplitId || null,
            week_starts_on: weekStartsOn,
            default_water_goal_ml: Number(waterGoal),
            water_quick_add_ml: parsedQuickAdds,
            default_target_rir: Number(targetRir),
            default_load_increment_kg: Number(loadIncrement),
            reduced_motion_override: reducedMotion,
            visibility,
          },
        }),
      ]);
      if (!profileResult.data || profileResult.error || !settingsResult.data || settingsResult.error) {
        throw new Error("Settings update failed");
      }
      applyMotionPreference(reducedMotion);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["public-dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["public-profile"] }),
        queryClient.invalidateQueries({ queryKey: ["splits"] }),
        queryClient.invalidateQueries({ queryKey: ["settings"] }),
      ]);
      setMessage("Settings saved.");
    } catch {
      setError("Settings could not be saved. Check each value and try again.");
    } finally {
      setIsSaving(false);
    }
  }

  function startExport(format: "json" | "csv") {
    setExportState("working");
    void downloadExport(format)
      .then(() => setExportState("success"))
      .catch(() => setExportState("error"));
  }

  return (
    <>
      <form className="settings-form" onSubmit={(event) => void save(event)}>
        <section className="settings-card" aria-labelledby="profile-settings-heading">
          <p className="card-label">Owner profile</p>
          <h2 id="profile-settings-heading">Profile and display</h2>
          <div className="settings-fields">
            <label>Display name<input maxLength={100} onChange={(event) => setDisplayName(event.target.value)} required value={displayName} /></label>
            <label>Preferred units<select onChange={(event) => setPreferredUnits(event.target.value as Profile["preferred_units"])} value={preferredUnits}><option value="imperial">Imperial</option><option value="metric">Metric</option></select></label>
            <label>Time zone<input onChange={(event) => setTimezone(event.target.value)} placeholder="America/Toronto" required value={timezone} /></label>
            <label>Height (cm)<input inputMode="numeric" max="250" min="100" onChange={(event) => setHeight(event.target.value)} type="number" value={height} /></label>
            <label>Body weight (kg)<input inputMode="decimal" max="400" min="20" onChange={(event) => setBodyWeight(event.target.value)} step="0.01" type="number" value={bodyWeight} /></label>
          </div>
        </section>

        <section className="settings-card" aria-labelledby="training-settings-heading">
          <p className="card-label">Training defaults</p>
          <h2 id="training-settings-heading">Plan and progression</h2>
          <div className="settings-fields">
            <label>Active split<select onChange={(event) => setActiveSplitId(event.target.value)} value={activeSplitId}><option value="">No active split</option>{splits.map((split) => <option key={split.id} value={split.id}>{split.name}</option>)}</select></label>
            <label>Week starts on<select onChange={(event) => setWeekStartsOn(Number(event.target.value))} value={weekStartsOn}><option value="0">Sunday</option><option value="1">Monday</option><option value="2">Tuesday</option><option value="3">Wednesday</option><option value="4">Thursday</option><option value="5">Friday</option><option value="6">Saturday</option></select></label>
            <label>Default target RIR<input inputMode="decimal" max="10" min="0" onChange={(event) => setTargetRir(event.target.value)} step="0.5" type="number" value={targetRir} /></label>
            <label>Load increment (kg)<input inputMode="decimal" min="0.000001" onChange={(event) => setLoadIncrement(event.target.value)} step="any" type="number" value={loadIncrement} /></label>
          </div>
        </section>

        <section className="settings-card" aria-labelledby="hydration-settings-heading">
          <p className="card-label">Hydration</p>
          <h2 id="hydration-settings-heading">Goal and quick-add</h2>
          <div className="settings-fields">
            <label>Daily water goal (mL)<input inputMode="numeric" max="10000" min="250" onChange={(event) => setWaterGoal(event.target.value)} required type="number" value={waterGoal} /></label>
            <label>Quick-add amounts (mL, comma-separated)<input onChange={(event) => setQuickAdds(event.target.value)} required value={quickAdds} /></label>
          </div>
        </section>

        <section className="settings-card settings-card--wide" aria-labelledby="privacy-settings-heading">
          <p className="card-label">Public visibility</p>
          <h2 id="privacy-settings-heading">Choose exactly what visitors see</h2>
          <div className="visibility-grid">
            {visibilityOptions.map((option) => (
              <label className="visibility-option" key={option.key}>
                <input checked={Boolean(visibility[option.key])} onChange={(event) => toggleVisibility(option.key, event.target.checked)} type="checkbox" />
                <span><strong>{option.label}</strong><small>{option.hint}</small></span>
              </label>
            ))}
          </div>
        </section>

        <section className="settings-card" aria-labelledby="motion-settings-heading">
          <p className="card-label">Accessibility</p>
          <h2 id="motion-settings-heading">Motion preference</h2>
          <label className="settings-single-field">Animation<select onChange={(event) => setMotion(event.target.value as typeof motion)} value={motion}><option value="system">Follow device setting</option><option value="reduce">Reduce motion</option><option value="full">Allow motion</option></select></label>
        </section>

        <div className="settings-save settings-card--wide">
          {message ? <p className="form-success" role="status">{message}</p> : null}
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <button className="button button--primary" disabled={isSaving} type="submit">{isSaving ? "Saving…" : "Save settings"}</button>
        </div>
      </form>

      <section className="settings-card settings-tools" aria-labelledby="data-tools-heading">
        <p className="card-label">Owner tools</p>
        <h2 id="data-tools-heading">Backup and access</h2>
        <p className="muted-copy">Download a complete backup before major plan or account changes.</p>
        <div className="settings-tool-actions">
          <button className="button" disabled={exportState === "working"} onClick={() => startExport("json")} type="button">Download JSON</button>
          <button className="button" disabled={exportState === "working"} onClick={() => startExport("csv")} type="button">Download CSV</button>
          <button className="button button--danger" onClick={() => { logout(); navigate("/"); }} type="button">Sign out</button>
        </div>
        {exportState === "success" ? <p className="form-success" role="status">Export ready.</p> : null}
        {exportState === "error" ? <p className="form-error" role="alert">The export could not be downloaded.</p> : null}
      </section>
    </>
  );
}

export function SettingsPage() {
  const { isAuthenticated } = useAuth();
  const query = useQuery({
    queryKey: ["settings-page"],
    queryFn: loadSettingsPage,
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (query.data) applyMotionPreference(query.data.settings.reduced_motion_override);
  }, [query.data]);

  return (
    <article className="page-shell settings-page">
      <header className="page-heading">
        <p className="eyebrow">OWNER CONTROLS</p>
        <h1>Settings</h1>
        <p>Manage your profile, training defaults, privacy, hydration, and personal data.</p>
      </header>

      {!isAuthenticated ? (
        <section className="settings-signin">
          <h2>Owner sign-in required</h2>
          <p>These controls change private account and public visibility settings.</p>
          <Link className="button button--primary" to="/login">Sign in to continue</Link>
        </section>
      ) : null}
      {isAuthenticated && query.isPending ? <LoadingState /> : null}
      {isAuthenticated && query.isError ? <ErrorState message="Settings could not be loaded." onRetry={() => void query.refetch()} /> : null}
      {query.data ? <SettingsForm {...query.data} /> : null}
    </article>
  );
}
