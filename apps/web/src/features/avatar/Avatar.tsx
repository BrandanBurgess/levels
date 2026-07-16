import { useId, useMemo, useState, type KeyboardEvent, type ReactNode } from "react";

import { DEFAULT_AVATAR_APPEARANCE, type AuraTier, type AvatarAppearance } from "./appearance";
import {
  AVATAR_REGION_LABELS,
  BACK_REGION_IDS,
  FRONT_REGION_IDS,
  isAvatarRegionId,
  type AvatarRegionId,
} from "./regions";
import "./Avatar.css";

export type AvatarHighlightRole = "primary" | "secondary" | "stabilizer";
export type { AuraTier, AvatarAppearance } from "./appearance";

export interface AvatarTarget {
  displayName: string;
  regionIds: string[];
  role: AvatarHighlightRole;
}

export interface AvatarProps {
  appearance?: AvatarAppearance;
  auraTier?: AuraTier;
  reducedMotion?: boolean;
  targets?: AvatarTarget[];
  view?: "front" | "back" | "both";
}

type RegionShape = { d: string };
type RegionDefinition = { id: AvatarRegionId; shapes: RegionShape[] };
type ResolvedTarget = { displayNames: string[]; role: AvatarHighlightRole };

const ROLE_PRIORITY: Record<AvatarHighlightRole, number> = {
  primary: 3,
  secondary: 2,
  stabilizer: 1,
};

const FRONT_REGIONS: RegionDefinition[] = [
  { id: "delts_front", shapes: [{ d: "M102 137c10-13 19-17 28-15l-8 35-21 12z" }, { d: "M198 137c-10-13-19-17-28-15l8 35 21 12z" }] },
  { id: "delts_side", shapes: [{ d: "M91 143c8-10 13-12 20-13l-10 39-14-3z" }, { d: "M209 143c-8-10-13-12-20-13l10 39 14-3z" }] },
  { id: "chest_upper", shapes: [{ d: "M126 123c8-7 15-10 23-10v30h-28z" }, { d: "M174 123c-8-7-15-10-23-10v30h28z" }] },
  { id: "chest_mid", shapes: [{ d: "M121 146h28v31l-31-4z" }, { d: "M179 146h-28v31l31-4z" }] },
  { id: "chest_lower", shapes: [{ d: "M118 176l31 4v22c-13-1-24-7-34-16z" }, { d: "M182 176l-31 4v22c13-1 24-7 34-16z" }] },
  { id: "biceps", shapes: [{ d: "M83 174c8-7 16-7 22 0l-8 55-20-4z" }, { d: "M217 174c-8-7-16-7-22 0l8 55 20-4z" }] },
  { id: "brachialis", shapes: [{ d: "M77 224l20 5-7 23-18-5z" }, { d: "M223 224l-20 5 7 23 18-5z" }] },
  { id: "forearms", shapes: [{ d: "M71 249l19 5-17 71-23-5z" }, { d: "M229 249l-19 5 17 71 23-5z" }] },
  { id: "abs", shapes: [{ d: "M136 205h13v88h-18l-5-74z" }, { d: "M164 205h-13v88h18l5-74z" }] },
  { id: "obliques", shapes: [{ d: "M113 196l12 20 5 75-19-16z" }, { d: "M187 196l-12 20-5 75 19-16z" }] },
  { id: "hip_flexors", shapes: [{ d: "M115 278l34 17-1 35-39-7z" }, { d: "M185 278l-34 17 1 35 39-7z" }] },
  { id: "abductors", shapes: [{ d: "M106 331l37 4-8 65-36-10z" }, { d: "M194 331l-37 4 8 65 36-10z" }] },
  { id: "quads", shapes: [{ d: "M103 350l39-8-11 119-38-4z" }, { d: "M197 350l-39-8 11 119 38-4z" }] },
  { id: "adductors", shapes: [{ d: "M142 345h7l-4 105-17-37z" }, { d: "M158 345h-7l4 105 17-37z" }] },
  { id: "calves", shapes: [{ d: "M96 458l35 6-8 43h-26z" }, { d: "M204 458l-35 6 8 43h26z" }] },
];

const BACK_REGIONS: RegionDefinition[] = [
  { id: "traps", shapes: [{ d: "M129 105l20 15-20 38-21-22z" }, { d: "M171 105l-20 15 20 38 21-22z" }] },
  { id: "delts_rear", shapes: [{ d: "M103 134c11-12 20-14 29-11l-8 38-25 8z" }, { d: "M197 134c-11-12-20-14-29-11l8 38 25 8z" }] },
  { id: "upper_back", shapes: [{ d: "M127 135l22-12v61l-36-17z" }, { d: "M173 135l-22-12v61l36-17z" }] },
  { id: "lats", shapes: [{ d: "M112 170l37 17-9 79-32-33z" }, { d: "M188 170l-37 17 9 79 32-33z" }] },
  { id: "spinal_erectors", shapes: [{ d: "M140 184h9v106l-18-8z" }, { d: "M160 184h-9v106l18-8z" }] },
  { id: "triceps", shapes: [{ d: "M82 170c8-7 17-7 23 0l-8 68-22-5z" }, { d: "M218 170c-8-7-17-7-23 0l8 68 22-5z" }] },
  { id: "forearms", shapes: [{ d: "M74 239l23 5-24 81-23-5z" }, { d: "M226 239l-23 5 24 81 23-5z" }] },
  { id: "glutes", shapes: [{ d: "M108 291l41 4v49l-45-8z" }, { d: "M192 291l-41 4v49l45-8z" }] },
  { id: "hamstrings", shapes: [{ d: "M103 345l40 3-12 111-38-3z" }, { d: "M197 345l-40 3 12 111 38-3z" }] },
  { id: "calves", shapes: [{ d: "M96 458l35 6-8 43h-26z" }, { d: "M204 458l-35 6 8 43h26z" }] },
];

function resolveTargets(targets: AvatarTarget[]) {
  const resolved = new Map<AvatarRegionId, ResolvedTarget>();
  for (const target of targets) {
    for (const regionId of target.regionIds) {
      if (!isAvatarRegionId(regionId)) continue;
      const current = resolved.get(regionId);
      const displayNames = current?.displayNames.includes(target.displayName)
        ? current.displayNames
        : [...(current?.displayNames ?? []), target.displayName];
      const role = !current || ROLE_PRIORITY[target.role] > ROLE_PRIORITY[current.role]
        ? target.role
        : current.role;
      resolved.set(regionId, { displayNames, role });
    }
  }
  return resolved;
}

function onRegionKeyDown(event: KeyboardEvent<SVGGElement>, select: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    select();
  }
}

function MuscleRegions({
  definitions,
  interactiveRegionIds,
  onSelect,
  targets,
}: {
  definitions: RegionDefinition[];
  interactiveRegionIds: ReadonlySet<AvatarRegionId>;
  onSelect: (regionId: AvatarRegionId) => void;
  targets: Map<AvatarRegionId, ResolvedTarget>;
}) {
  return (
    <g data-layer="muscle-regions">
      {definitions.map(({ id, shapes }) => {
        const target = targets.get(id);
        const interactive = Boolean(target) && interactiveRegionIds.has(id);
        const select = () => onSelect(id);
        return (
          <g
            {...(interactive
              ? {
                  "aria-label": `${AVATAR_REGION_LABELS[id]}: ${target?.role ?? "idle"} target`,
                  onClick: select,
                  onFocus: select,
                  onKeyDown: (event: KeyboardEvent<SVGGElement>) => onRegionKeyDown(event, select),
                  role: "button",
                  tabIndex: 0,
                }
              : { "aria-hidden": true })}
            className={`avatar-region avatar-region--${target?.role ?? "idle"}`}
            data-highlight-cue={target?.role === "secondary" ? "dashed" : target?.role === "stabilizer" ? "dotted" : target?.role === "primary" ? "solid-bold" : "none"}
            data-region-id={id}
            key={id}
            onMouseEnter={target ? select : undefined}
          >
            {shapes.map((shape, index) => (
              <path data-region-id={id} d={shape.d} key={`${id}-${index}`} vectorEffect="non-scaling-stroke" />
            ))}
          </g>
        );
      })}
    </g>
  );
}

function MaleBase({ view }: { view: "front" | "back" }) {
  return (
    <g data-base="male" data-layer="base">
      <circle className="avatar__skin" cx="150" cy="70" data-avatar-face="skin" r="37" />
      <path className="avatar__skin" d="M128 101c-9 14-17 24-35 30l20 213h74l20-213c-18-6-26-16-35-30z" />
      <path className="avatar__skin" d="M100 130c-20 9-31 28-36 56L43 325c-3 19 23 24 29 6l37-123z" />
      <path className="avatar__skin" d="M200 130c20 9 31 28 36 56l21 139c3 19-23 24-29 6l-37-123z" />
      <path className="avatar__skin" d="M116 326L96 499c-2 20 25 24 31 5l23-130 23 130c6 19 33 15 31-5l-20-173z" />
      <path className="avatar__outline" d={view === "front" ? "M137 71h5m16 0h5m-20 17c5 3 9 4 14 0" : "M150 108v180"} />
    </g>
  );
}

function FemaleBase({ view }: { view: "front" | "back" }) {
  return (
    <g data-base="female" data-layer="base">
      <ellipse className="avatar__skin" cx="150" cy="70" data-avatar-face="skin" rx="34" ry="38" />
      <path className="avatar__skin" d="M130 102c-8 13-17 21-32 28l16 120-13 94h98l-13-94 16-120c-15-7-24-15-32-28-12 8-28 8-40 0z" />
      <path className="avatar__skin" d="M101 130c-18 9-27 29-32 55L47 324c-3 18 21 23 27 6l35-122z" />
      <path className="avatar__skin" d="M199 130c18 9 27 29 32 55l22 139c3 18-21 23-27 6l-35-122z" />
      <path className="avatar__skin" d="M108 326L94 499c-2 20 25 24 31 5l25-132 25 132c6 19 33 15 31-5l-14-173z" />
      <path className="avatar__outline" d={view === "front" ? "M137 71h5m16 0h5m-19 17c4 3 8 3 12 0" : "M150 108v180"} />
    </g>
  );
}

function RearHairLayer({ appearance }: { appearance: AvatarAppearance }) {
  const hairstyle = appearance.hairstyle;
  const hasRearLayer = ["short_locs", "locs", "braids", "long_curls", "curly_bob", "bun", "bob", "covered"].includes(hairstyle);
  if (!hasRearLayer) return null;

  return (
    <g className={`avatar__hair avatar__hair--${hairstyle}`} data-hair-layer="rear" data-hairstyle={hairstyle} data-layer="hair">
      {hairstyle === "short_locs" ? (
        <g className="avatar__hair-strands avatar__hair-strands--short-locs" data-hair-texture="short-locs">
          <path d="M116 45q-9 23-8 49M126 35q-7 28-5 57M139 29q-4 29-2 61M160 29q4 31 2 62M174 35q8 28 5 57M184 45q9 23 8 49" />
        </g>
      ) : null}
      {hairstyle === "locs" ? (
        <g className="avatar__hair-strands avatar__hair-strands--locs" data-hair-texture="locs">
          <path d="M119 48q-8 43-3 110M128 35q-7 67-2 139M139 28q-4 73-1 153M151 26q2 78 0 158M162 29q7 76 3 151M173 37q10 64 5 136M181 49q9 48 5 108" />
        </g>
      ) : null}
      {hairstyle === "braids" ? (
        <g className="avatar__hair-strands avatar__hair-strands--braids" data-hair-texture="braids">
          <path d="M122 47q-8 45-4 129M134 32q-6 72-2 162M147 27q-3 80-1 174M159 29q5 83 3 169M172 37q9 69 5 151M181 50q10 49 7 124" />
          <circle cx="118" cy="176" r="3" /><circle cx="132" cy="194" r="3" /><circle cx="146" cy="201" r="3" />
          <circle cx="162" cy="198" r="3" /><circle cx="177" cy="188" r="3" /><circle cx="188" cy="174" r="3" />
        </g>
      ) : null}
      {hairstyle === "long_curls" ? (
        <>
          <path d="M113 68c-2-31 14-53 37-53 25 0 40 23 38 54l10 35-9 28 9 30-13 19 5 30-25-7-15 12-15-12-25 7 5-30-13-19 9-30-9-28z" />
          <g className="avatar__hair-detail avatar__hair-detail--stroke avatar__hair-detail--curls" data-hair-texture="long-curls">
            <path d="M108 82q16-18 28 0t27 0t27 0M111 115q14-18 26 0t26 0t25 0M115 150q13-19 25 0t24 0t22 0M120 184q11-16 22 0t22 0" />
          </g>
        </>
      ) : null}
      {hairstyle === "curly_bob" ? (
        <>
          <path d="M113 67c-1-31 15-51 37-51 24 0 39 21 38 52l7 25-9 20 6 21-20 7-22-9-22 9-20-7 6-21-9-20z" />
          <g className="avatar__hair-detail avatar__hair-detail--stroke avatar__hair-detail--curls" data-hair-texture="curly-bob">
            <path d="M109 78q15-17 27 0t26 0t26 0M112 107q14-16 26 0t25 0t23 0" />
          </g>
        </>
      ) : null}
      {hairstyle === "bun" ? <circle cx="150" cy="15" r="18" /> : null}
      {hairstyle === "bob" ? <path d="M113 69c0-31 15-51 37-51s38 20 38 51l4 56-21 18-8-34h-26l-8 34-21-18z" /> : null}
      {hairstyle === "covered" ? <path className="avatar__hair-covering" d="M112 70c0-34 16-56 38-56 24 0 40 23 39 57l-5 48-20-18h-28l-20 18z" /> : null}
    </g>
  );
}

function FrontHairLayer({ appearance, view }: { appearance: AvatarAppearance; view: "front" | "back" }) {
  const hairstyle = appearance.hairstyle;
  if (hairstyle === "bald") return null;
  const crown = <path d="M114 69c0-31 15-51 36-51s37 20 37 51c-9-13-20-19-36-19-17 0-28 6-37 19z" />;

  return (
    <g className={`avatar__hair avatar__hair--${hairstyle}`} data-hair-layer="front" data-hairstyle={hairstyle} data-layer="hair">
      {hairstyle === "short_coils" ? (
        <>
          <path d="M115 65c0-25 14-43 35-43 22 0 37 18 37 43-9-12-19-17-36-18-16 0-27 5-36 18z" />
          <g className="avatar__hair-detail avatar__hair-detail--coils" data-hair-texture="coils">
            <circle cx="123" cy="43" r="5" /><circle cx="134" cy="33" r="6" /><circle cx="148" cy="29" r="6" />
            <circle cx="162" cy="31" r="6" /><circle cx="175" cy="40" r="5" />
          </g>
        </>
      ) : null}
      {hairstyle === "fade" ? <path d="M117 62c2-23 15-37 33-37 20 0 33 15 35 37-10-9-21-13-34-13-14 0-25 4-34 13z" /> : null}
      {hairstyle === "waves" ? (
        <>
          <path d="M116 63c1-24 15-39 34-39 21 0 35 16 36 39-10-10-21-14-35-14-15 0-26 4-35 14z" />
          <g className="avatar__hair-detail avatar__hair-detail--stroke" data-hair-texture="waves"><path d="M125 45q9-9 18 0t18 0t17 0M130 34q8-6 16 0t16 0" /></g>
        </>
      ) : null}
      {["short_locs", "locs", "braids", "bun", "bob"].includes(hairstyle) ? crown : null}
      {["long_curls", "curly_bob"].includes(hairstyle) ? (
        <>
          {crown}
          <g className="avatar__hair-detail avatar__hair-detail--stroke avatar__hair-detail--curls avatar__hair-detail--hairline" data-hair-texture={`${hairstyle}-hairline`}>
            <path d="M118 50q13-16 25 0t25 0M127 34q10-10 20 0t19 0" />
          </g>
        </>
      ) : null}
      {hairstyle === "short_straight" ? <path d="M114 68c0-29 15-48 36-48 23 0 38 20 38 49l-10-14-10 8-10-9-10 9-11-8-14 14z" /> : null}
      {hairstyle === "covered" ? <path className="avatar__hair-covering" d="M114 68c0-32 15-53 36-53 23 0 38 22 38 54-11-12-23-18-38-18-16 0-27 6-36 17z" /> : null}
      {view === "back" && ["fade", "waves", "short_straight"].includes(hairstyle) ? <path className="avatar__hair-nape" d="M127 57q23 17 46 0l-4 39q-19 14-38 0z" /> : null}
    </g>
  );
}

function OutfitLayer({ appearance, view }: { appearance: AvatarAppearance; view: "front" | "back" }) {
  return (
    <g className={`avatar__outfit avatar__outfit--${appearance.outfit_style}`} data-layer="outfit">
      {appearance.outfit_style !== "tank_and_shorts" ? <path d="M104 132l25-18h42l25 18-12 116-68 0z" /> : null}
      {appearance.outfit_style === "tank_and_shorts" ? <path d="M126 118h48l13 122-74 0z" /> : null}
      <path d="M108 313h84l10 58-44-5-8-26-8 26-44 5z" />
      <path className="avatar__outfit-trim" d={`M109 318h82M150 319v21${view === "front" ? "M132 126h36" : ""}`} />
    </g>
  );
}

function AccessoryLayer({ accessory, view }: { accessory: AvatarAppearance["accessory"]; view: "front" | "back" }) {
  if (accessory === "none") return null;
  return (
    <g className="avatar__accessory" data-accessory={accessory} data-layer="accessory">
      {accessory === "glasses" ? <path d="M123 66h22v14h-22zM155 66h22v14h-22zM145 71h10" /> : null}
      {accessory === "headband" ? <path d="M117 53q33-13 66 0l-2 9q-31-11-62 0z" /> : null}
      {accessory === "wristbands" ? <path d="M61 286l20 4-4 17-20-4zM239 286l-20 4 4 17 20-4z" /> : null}
      {accessory === "cap" ? (
        <g className="avatar__accessory-cap">
          <path d="M116 52q4-35 34-35t35 35q-35-13-69 0z" />
          <path d={view === "front" ? "M116 51q40-13 78 7-38 6-77 1z" : "M116 51q34-12 69 0l-2 9q-32-9-65 0z"} />
        </g>
      ) : null}
    </g>
  );
}

export function Aura({ enabled, style, tier }: { enabled: boolean; style: AvatarAppearance["aura_style"]; tier: AuraTier }) {
  if (!enabled || tier === "none") return null;
  return (
    <g aria-hidden="true" className={`avatar-aura avatar-aura--${tier} avatar-aura--${style}`} data-aura-tier={tier} data-layer="aura">
      <ellipse className="avatar-aura__glow" cx="150" cy="282" rx="112" ry="246" />
      {style === "rings" ? <><ellipse className="avatar-aura__ring avatar-aura__ring--one" cx="150" cy="290" rx="125" ry="230" /><ellipse className="avatar-aura__ring avatar-aura__ring--two" cx="150" cy="290" rx="105" ry="250" /></> : null}
      {style === "sparks" ? <><path className="avatar-aura__spark avatar-aura__spark--one" d="M38 145l8-18 5 20-9 15z" /><path className="avatar-aura__spark avatar-aura__spark--two" d="M256 302l9-20 4 22-10 14z" /></> : null}
    </g>
  );
}

function AppearanceLayers({ appearance, view }: { appearance: AvatarAppearance; view: "front" | "back" }) {
  return (
    <>
      <RearHairLayer appearance={appearance} />
      {appearance.base_presentation === "male" ? <MaleBase view={view} /> : <FemaleBase view={view} />}
      <OutfitLayer appearance={appearance} view={view} />
      <FrontHairLayer appearance={appearance} view={view} />
      <AccessoryLayer accessory={appearance.accessory} view={view} />
    </>
  );
}

function AvatarView({
  appearance,
  auraTier,
  definitions,
  interactiveRegionIds,
  label,
  onSelect,
  targets,
  transform,
  view,
}: {
  appearance: AvatarAppearance;
  auraTier: AuraTier;
  definitions: RegionDefinition[];
  interactiveRegionIds: ReadonlySet<AvatarRegionId>;
  label: string;
  onSelect: (regionId: AvatarRegionId) => void;
  targets: Map<AvatarRegionId, ResolvedTarget>;
  transform: string;
  view: "front" | "back";
}) {
  return (
    <g className="avatar__view" data-view={view} transform={transform}>
      <text className="avatar__view-label" x="150" y="24">{label}</text>
      <ellipse className="avatar__ground" cx="150" cy="520" rx="92" ry="12" />
      <Aura enabled={appearance.aura_enabled} style={appearance.aura_style} tier={auraTier} />
      <g className={appearance.base_presentation === "female" ? "avatar__figure avatar__figure--female" : "avatar__figure"} data-hairstyle={appearance.hairstyle}>
        <AppearanceLayers appearance={appearance} view={view} />
        <MuscleRegions definitions={definitions} interactiveRegionIds={interactiveRegionIds} onSelect={onSelect} targets={targets} />
      </g>
    </g>
  );
}

type SemanticViewProps = Omit<Parameters<typeof AvatarView>[0], "definitions" | "label" | "transform" | "view">;

function FrontView(props: SemanticViewProps) {
  return <AvatarView {...props} definitions={FRONT_REGIONS} label="FRONT" transform="translate(10 10)" view="front" />;
}

function BackView(props: SemanticViewProps) {
  return <AvatarView {...props} definitions={BACK_REGIONS} label="BACK" transform="translate(370 10)" view="back" />;
}

export function RegionLegend() {
  return (
    <ul aria-label="Muscle highlight legend" className="avatar-legend">
      <li><span aria-hidden="true" className="avatar-legend__key avatar-legend__key--primary" />Primary · bold border and glow</li>
      <li><span aria-hidden="true" className="avatar-legend__key avatar-legend__key--secondary" />Secondary · dashed border</li>
      <li><span aria-hidden="true" className="avatar-legend__key avatar-legend__key--stabilizer" />Stabilizer · dotted outline</li>
    </ul>
  );
}

export function AccessibleRegionList({ targets }: { targets: AvatarTarget[] }) {
  if (targets.length === 0) return <p className="muted-copy">Recovery day · no planned targets.</p>;
  return (
    <ul aria-label="Muscles targeted today" className="avatar-targets">
      {targets.map((target, index) => (
        <li className={`avatar-target avatar-target--${target.role}`} key={`${target.displayName}-${target.role}-${index}`}>
          <span aria-hidden="true" className="avatar-target__cue" />
          <span>{target.displayName}</span>
          <small>{target.role}</small>
        </li>
      ))}
    </ul>
  );
}

export function AvatarFrame({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`avatar-frame ${className}`.trim()}>{children}</div>;
}

export function Avatar({
  appearance = DEFAULT_AVATAR_APPEARANCE,
  auraTier = "none",
  reducedMotion = false,
  targets = [],
  view = "both",
}: AvatarProps) {
  const titleId = useId();
  const descriptionId = useId();
  const [selectedRegion, setSelectedRegion] = useState<AvatarRegionId>();
  const resolvedTargets = useMemo(() => resolveTargets(targets), [targets]);
  const frontInteractive = useMemo<Set<AvatarRegionId>>(
    () => new Set(FRONT_REGION_IDS.filter((id) => resolvedTargets.has(id))),
    [resolvedTargets],
  );
  const backInteractive = useMemo<Set<AvatarRegionId>>(
    () => new Set(BACK_REGION_IDS.filter((id) => resolvedTargets.has(id) && (view !== "both" || !frontInteractive.has(id)))),
    [frontInteractive, resolvedTargets, view],
  );
  const selectedTarget = selectedRegion ? resolvedTargets.get(selectedRegion) : undefined;
  const viewBox = view === "front" ? "0 0 320 560" : view === "back" ? "360 0 320 560" : "0 0 680 560";
  const baseLabel = appearance.base_presentation === "male" ? "male" : "female";

  return (
    <AvatarFrame className={`avatar avatar--${view} avatar--background-${appearance.background}`}>
      <figure
        data-avatar-view={view}
        data-base-presentation={appearance.base_presentation}
        data-hair-color={appearance.hair_color}
        data-outfit-palette={appearance.outfit_palette}
        data-reduced-motion={reducedMotion ? "true" : "false"}
        data-skin-tone={appearance.skin_tone}
      >
        <svg aria-describedby={descriptionId} aria-labelledby={titleId} className="avatar__art" role="img" viewBox={viewBox}>
          <title id={titleId}>{view === "both" ? `Front and back ${baseLabel} muscle avatar` : `${view} ${baseLabel} muscle avatar`}</title>
          <desc id={descriptionId}>Layered original avatar artwork. Highlight roles use border patterns and the text list below in addition to color.</desc>
          {view !== "back" ? <FrontView appearance={appearance} auraTier={auraTier} interactiveRegionIds={frontInteractive} onSelect={setSelectedRegion} targets={resolvedTargets} /> : null}
          {view !== "front" ? <BackView appearance={appearance} auraTier={auraTier} interactiveRegionIds={backInteractive} onSelect={setSelectedRegion} targets={resolvedTargets} /> : null}
        </svg>
        <figcaption className="avatar__caption">
          {selectedRegion && selectedTarget ? (
            <p className="avatar__region-callout" role="status"><strong>{AVATAR_REGION_LABELS[selectedRegion]}</strong> · {selectedTarget.role} · {selectedTarget.displayNames.join(", ")}</p>
          ) : <p className="avatar__interaction-hint">Focus or tap a highlighted region for details.</p>}
          <RegionLegend />
          <AccessibleRegionList targets={targets} />
        </figcaption>
      </figure>
    </AvatarFrame>
  );
}
