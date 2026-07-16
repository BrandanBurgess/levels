import type { components } from "@levels/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { apiClient } from "../../api/client";
import { ErrorState, LoadingState } from "../../ui/AsyncState";
import { Avatar, type AvatarAppearance, type AvatarTarget } from "../avatar/Avatar";
import "./AppearancePanel.css";

type StreakSummary = components["schemas"]["StreakSummary"];
type Settings = components["schemas"]["Settings"];

const LABELS = {
  base_presentation: { male: "Male", female: "Female" },
  skin_tone: { deep: "Deep", rich: "Rich", medium_deep: "Medium deep", medium: "Medium", light_medium: "Light medium", light: "Light" },
  hairstyle: { short_coils: "Short coils", fade: "Fade", waves: "Waves", short_locs: "Short locs", locs: "Long locs", braids: "Long braids", long_curls: "Long curls", curly_bob: "Curly bob", bun: "Bun", bob: "Bob", short_straight: "Short straight", covered: "Covered", bald: "Bald" },
  hair_color: { black: "Black", dark_brown: "Dark brown", brown: "Brown", auburn: "Auburn", gray: "Gray", blonde: "Blonde" },
  outfit_style: { training_tee: "Training tee", tank_and_shorts: "Tank and shorts", long_sleeve: "Long sleeve", modest_activewear: "Modest activewear" },
  outfit_palette: { violet: "Violet", teal: "Teal", blue: "Blue", rose: "Rose", neutral: "Neutral" },
  accessory: { none: "None", glasses: "Glasses", headband: "Headband", wristbands: "Wristbands", cap: "Cap" },
  background: { none: "None", gradient: "Gradient", gym: "Gym", dusk: "Dusk" },
  aura_style: { standard: "Standard glow", rings: "Rings", sparks: "Sparks" },
} as const;

const PREVIEW_TARGETS: AvatarTarget[] = [
  { displayName: "Chest", regionIds: ["chest_mid"], role: "primary" },
  { displayName: "Triceps", regionIds: ["triceps"], role: "secondary" },
  { displayName: "Core stability", regionIds: ["abs"], role: "stabilizer" },
];

async function fetchAppearance(): Promise<{
  avatar: AvatarAppearance;
  settings: Settings;
  streak: StreakSummary;
}> {
  const [avatarResult, settingsResult, streakResult] = await Promise.all([
    apiClient.GET("/me/avatar"),
    apiClient.GET("/settings"),
    apiClient.GET("/me/streak"),
  ]);
  if (!avatarResult.data || avatarResult.error || !settingsResult.data || settingsResult.error || !streakResult.data || streakResult.error) {
    throw new Error("Appearance request failed");
  }
  return { avatar: avatarResult.data, settings: settingsResult.data, streak: streakResult.data };
}

function SelectControl<K extends keyof Pick<AvatarAppearance, "hairstyle" | "hair_color" | "outfit_style" | "outfit_palette" | "accessory" | "background" | "aura_style">>({
  field,
  label,
  onChange,
  value,
}: {
  field: K;
  label: string;
  onChange: (field: K, value: AvatarAppearance[K]) => void;
  value: AvatarAppearance[K];
}) {
  const labels = LABELS[field] as Record<string, string>;
  return (
    <label className="appearance-control">
      <span>{label}</span>
      <select onChange={(event) => onChange(field, event.target.value as AvatarAppearance[K])} value={value}>
        {Object.entries(labels).map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

export function AppearancePanel() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["character-appearance"], queryFn: fetchAppearance });
  const [draft, setDraft] = useState<AvatarAppearance>();
  const [previewView, setPreviewView] = useState<"front" | "back">("front");
  const [showHighlights, setShowHighlights] = useState(true);

  useEffect(() => {
    if (query.data?.avatar) setDraft(query.data.avatar);
  }, [query.data?.avatar]);

  const mutation = useMutation({
    mutationFn: async (appearance: AvatarAppearance) => {
      const { data, error } = await apiClient.PATCH("/me/avatar", { body: appearance });
      if (!data || error) throw new Error("Appearance update failed");
      return data;
    },
    onSuccess: (avatar) => {
      setDraft(avatar);
      queryClient.setQueryData<Awaited<ReturnType<typeof fetchAppearance>>>(
        ["character-appearance"],
        (current) => current ? { ...current, avatar } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["character-overview"] });
      void queryClient.invalidateQueries({ queryKey: ["today"] });
    },
  });

  function update<K extends keyof AvatarAppearance>(field: K, value: AvatarAppearance[K]) {
    setDraft((current) => current ? { ...current, [field]: value } : current);
    mutation.reset();
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (draft) mutation.mutate(draft);
  }

  if (query.isError) {
    return <ErrorState message="Appearance settings could not be loaded." onRetry={() => void query.refetch()} />;
  }
  if (query.isPending || !query.data || !draft) return <LoadingState />;

  return (
    <section aria-labelledby="appearance-heading" className="appearance-panel">
      <div className="appearance-panel__intro">
        <p className="card-label">Personal style</p>
        <h2 id="appearance-heading">Appearance</h2>
        <p>Choose a presentation and cosmetic details. These controls never score, compare, or estimate your body.</p>
      </div>

      <div className="appearance-layout">
        <div className="appearance-preview">
          <div className="card-heading-row">
            <div>
              <p className="card-label">Live preview</p>
              <h3>{previewView === "front" ? "Front view" : "Back view"}</h3>
            </div>
            <div aria-label="Appearance preview view" className="segmented-control" role="group">
              <button aria-pressed={previewView === "front"} onClick={() => setPreviewView("front")} type="button">Front</button>
              <button aria-pressed={previewView === "back"} onClick={() => setPreviewView("back")} type="button">Back</button>
            </div>
          </div>
          <Avatar
            appearance={draft}
            auraTier={query.data.streak.tier}
            reducedMotion={query.data.settings.reduced_motion_override === true}
            targets={showHighlights ? PREVIEW_TARGETS : []}
            view={previewView}
          />
          <label className="appearance-highlight-toggle">
            <input checked={showHighlights} onChange={(event) => setShowHighlights(event.target.checked)} type="checkbox" />
            Preview muscle highlight roles
          </label>
          <p className="appearance-streak-copy">
            Current streak: <strong>{query.data.streak.current_count}</strong> · {query.data.streak.tier} aura
          </p>
        </div>

        <form className="appearance-form" onSubmit={submit}>
          <fieldset>
            <legend>Base presentation</legend>
            <div className="appearance-choice-row">
              {Object.entries(LABELS.base_presentation).map(([value, label]) => (
                <label key={value}>
                  <input checked={draft.base_presentation === value} name="base-presentation" onChange={() => update("base_presentation", value as AvatarAppearance["base_presentation"])} type="radio" />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend>Skin tone</legend>
            <div className="appearance-swatch-row">
              {Object.entries(LABELS.skin_tone).map(([value, label]) => (
                <label key={value}>
                  <input aria-label={label} checked={draft.skin_tone === value} name="skin-tone" onChange={() => update("skin_tone", value as AvatarAppearance["skin_tone"])} type="radio" />
                  <span aria-hidden="true" className={`appearance-swatch appearance-swatch--${value}`} />
                </label>
              ))}
            </div>
          </fieldset>

          <div className="appearance-control-grid">
            <SelectControl field="hairstyle" label="Hairstyle" onChange={update} value={draft.hairstyle} />
            <SelectControl field="hair_color" label="Hair color" onChange={update} value={draft.hair_color} />
            <SelectControl field="outfit_style" label="Outfit" onChange={update} value={draft.outfit_style} />
            <SelectControl field="outfit_palette" label="Outfit palette" onChange={update} value={draft.outfit_palette} />
            <SelectControl field="accessory" label="Accessory" onChange={update} value={draft.accessory} />
            <SelectControl field="background" label="Background" onChange={update} value={draft.background} />
            <SelectControl field="aura_style" label="Aura style" onChange={update} value={draft.aura_style} />
          </div>

          <label className="appearance-aura-toggle">
            <input checked={draft.aura_enabled} onChange={(event) => update("aura_enabled", event.target.checked)} type="checkbox" />
            <span><strong>Show streak aura</strong><small>Turn off the visual aura without changing your streak.</small></span>
          </label>

          {mutation.isError ? <p className="form-error" role="alert">Appearance changes could not be saved.</p> : null}
          {mutation.isSuccess ? <p className="form-success" role="status">Appearance saved.</p> : null}
          <button className="button button--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? "Saving…" : "Save appearance"}
          </button>
        </form>
      </div>
    </section>
  );
}
