export type AvatarHighlightRole = "primary" | "secondary" | "stabilizer";

export interface AvatarTarget {
  displayName: string;
  regionIds: string[];
  role: AvatarHighlightRole;
}

interface AvatarProps {
  targets?: AvatarTarget[];
  view?: "front" | "back" | "both";
}

function roleFor(regionId: string, targets: AvatarTarget[]) {
  const roles = targets.filter((target) => target.regionIds.includes(regionId)).map((target) => target.role);
  if (roles.includes("primary")) return "primary";
  if (roles.includes("secondary")) return "secondary";
  if (roles.includes("stabilizer")) return "stabilizer";
  return "idle";
}

function Region({
  id,
  targets,
  ...shape
}: React.SVGProps<SVGPathElement> & { id: string; targets: AvatarTarget[] }) {
  return (
    <path
      {...shape}
      aria-hidden="true"
      className={`avatar-region avatar-region--${roleFor(id, targets)}`}
      data-muscle-id={id}
      vectorEffect="non-scaling-stroke"
    />
  );
}

export function Avatar({ targets = [], view = "both" }: AvatarProps) {
  const viewBox = view === "front" ? "0 0 320 560" : view === "back" ? "360 0 320 560" : "0 0 680 560";
  return (
    <figure className={`avatar avatar--${view}`} data-avatar-view={view}>
      <svg
        aria-describedby="avatar-description"
        aria-labelledby="avatar-title"
        className="avatar__art"
        role="img"
        viewBox={viewBox}
      >
        <title id="avatar-title">Front and back muscle avatar</title>
        <desc id="avatar-description">
          Original illustrated Black male avatar. Purple regions show the muscles targeted by the current
          workout; the text list below gives the same information.
        </desc>

        <defs>
          <linearGradient id="avatar-skin" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#6f3f2d" />
            <stop offset="1" stopColor="#3a201a" />
          </linearGradient>
          <linearGradient id="avatar-shorts" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#241735" />
            <stop offset="1" stopColor="#110b1b" />
          </linearGradient>
          <filter id="avatar-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur in="SourceGraphic" result="blur" stdDeviation="7" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {view !== "back" ? <g className="avatar__view" data-view="front" transform="translate(10 10)">
          <text className="avatar__view-label" x="150" y="24">FRONT</text>
          <ellipse className="avatar__ground" cx="150" cy="520" rx="92" ry="12" />

          <g data-layer="skin">
            <circle className="avatar__skin" cx="150" cy="70" r="37" />
            <path className="avatar__skin" d="M128 101c-9 14-17 24-35 30l20 213h74l20-213c-18-6-26-16-35-30z" />
            <path className="avatar__skin" d="M100 130c-20 9-31 28-36 56l-21 139c-3 19 23 24 29 6l37-123z" />
            <path className="avatar__skin" d="M200 130c20 9 31 28 36 56l21 139c3 19-23 24-29 6l-37-123z" />
            <path className="avatar__skin" d="M116 326l-20 173c-2 20 25 24 31 5l23-130 23 130c6 19 33 15 31-5l-20-173z" />
          </g>

          <g data-layer="hair">
            <path className="avatar__hair" d="M115 65c0-25 14-43 35-43 22 0 37 18 37 43-9-12-19-17-36-18-16 0-27 5-36 18z" />
            <circle className="avatar__hair-detail" cx="127" cy="39" r="5" />
            <circle className="avatar__hair-detail" cx="143" cy="32" r="6" />
            <circle className="avatar__hair-detail" cx="160" cy="33" r="6" />
            <circle className="avatar__hair-detail" cx="176" cy="41" r="5" />
          </g>

          <g data-layer="highlights">
            <Region id="delts_front" targets={targets} d="M102 137c10-13 19-17 28-15l-8 35-21 12z" />
            <Region id="delts_front" targets={targets} d="M198 137c-10-13-19-17-28-15l8 35 21 12z" />
            <Region id="delts_side" targets={targets} d="M91 143c8-10 13-12 20-13l-10 39-14-3z" />
            <Region id="delts_side" targets={targets} d="M209 143c-8-10-13-12-20-13l10 39 14-3z" />
            <Region id="chest_upper" targets={targets} d="M126 123c8-7 15-10 23-10v30h-28z" />
            <Region id="chest_upper" targets={targets} d="M174 123c-8-7-15-10-23-10v30h28z" />
            <Region id="chest_mid" targets={targets} d="M121 146h28v31l-31-4z" />
            <Region id="chest_mid" targets={targets} d="M179 146h-28v31l31-4z" />
            <Region id="chest_lower" targets={targets} d="M118 176l31 4v22c-13-1-24-7-34-16z" />
            <Region id="chest_lower" targets={targets} d="M182 176l-31 4v22c13-1 24-7 34-16z" />
            <Region id="biceps" targets={targets} d="M83 174c8-7 16-7 22 0l-8 55-20-4z" />
            <Region id="biceps" targets={targets} d="M217 174c-8-7-16-7-22 0l8 55 20-4z" />
            <Region id="brachialis" targets={targets} d="M77 224l20 5-7 23-18-5z" />
            <Region id="brachialis" targets={targets} d="M223 224l-20 5 7 23 18-5z" />
            <Region id="forearms" targets={targets} d="M71 249l19 5-17 71-23-5z" />
            <Region id="forearms" targets={targets} d="M229 249l-19 5 17 71 23-5z" />
            <Region id="abs" targets={targets} d="M136 205h13v88h-18l-5-74z" />
            <Region id="abs" targets={targets} d="M164 205h-13v88h18l5-74z" />
            <Region id="obliques" targets={targets} d="M113 196l12 20 5 75-19-16z" />
            <Region id="obliques" targets={targets} d="M187 196l-12 20-5 75 19-16z" />
            <Region id="hip_flexors" targets={targets} d="M115 278l34 17-1 35-39-7z" />
            <Region id="hip_flexors" targets={targets} d="M185 278l-34 17 1 35 39-7z" />
            <Region id="abductors" targets={targets} d="M106 331l37 4-8 65-36-10z" />
            <Region id="abductors" targets={targets} d="M194 331l-37 4 8 65 36-10z" />
            <Region id="quads" targets={targets} d="M103 350l39-8-11 119-38-4z" />
            <Region id="quads" targets={targets} d="M197 350l-39-8 11 119 38-4z" />
            <Region id="adductors" targets={targets} d="M142 345h7l-4 105-17-37z" />
            <Region id="adductors" targets={targets} d="M158 345h-7l4 105 17-37z" />
            <Region id="calves" targets={targets} d="M96 458l35 6-8 43-26 0z" />
            <Region id="calves" targets={targets} d="M204 458l-35 6 8 43 26 0z" />
          </g>

          <g data-layer="clothing">
            <path className="avatar__shorts" d="M108 313h84l10 58-44-5-8-26-8 26-44 5z" />
            <path className="avatar__trim" d="M109 318h82M150 319v21" />
          </g>
          <g data-layer="outline">
            <path className="avatar__outline" d="M128 101c-9 14-17 24-35 30-20 9-31 28-36 56L43 325c-3 19 23 24 29 6l17-78 9 118-2 128c-2 20 25 24 31 5l23-130 23 130c6 19 33 15 31-5l-2-128 9-118 17 78c6 18 32 13 29-6l-14-138c-5-28-16-47-36-56-18-6-26-16-35-30" />
            <path className="avatar__face" d="M137 71h5m16 0h5m-20 17c5 3 9 4 14 0" />
          </g>
        </g> : null}

        {view !== "front" ? <g className="avatar__view" data-view="back" transform="translate(370 10)">
          <text className="avatar__view-label" x="150" y="24">BACK</text>
          <ellipse className="avatar__ground" cx="150" cy="520" rx="92" ry="12" />
          <g data-layer="skin">
            <circle className="avatar__skin" cx="150" cy="70" r="37" />
            <path className="avatar__skin" d="M128 101c-9 14-17 24-35 30l20 213h74l20-213c-18-6-26-16-35-30z" />
            <path className="avatar__skin" d="M100 130c-20 9-31 28-36 56l-21 139c-3 19 23 24 29 6l37-123z" />
            <path className="avatar__skin" d="M200 130c20 9 31 28 36 56l21 139c3 19-23 24-29 6l-37-123z" />
            <path className="avatar__skin" d="M116 326l-20 173c-2 20 25 24 31 5l23-130 23 130c6 19 33 15 31-5l-20-173z" />
          </g>
          <g data-layer="hair">
            <path className="avatar__hair" d="M115 65c0-25 14-43 35-43 22 0 37 18 37 43-9-12-19-17-36-18-16 0-27 5-36 18z" />
          </g>
          <g data-layer="highlights">
            <Region id="traps" targets={targets} d="M129 105l20 15-20 38-21-22z" />
            <Region id="traps" targets={targets} d="M171 105l-20 15 20 38 21-22z" />
            <Region id="delts_rear" targets={targets} d="M103 134c11-12 20-14 29-11l-8 38-25 8z" />
            <Region id="delts_rear" targets={targets} d="M197 134c-11-12-20-14-29-11l8 38 25 8z" />
            <Region id="upper_back" targets={targets} d="M127 135l22-12v61l-36-17z" />
            <Region id="upper_back" targets={targets} d="M173 135l-22-12v61l36-17z" />
            <Region id="lats" targets={targets} d="M112 170l37 17-9 79-32-33z" />
            <Region id="lats" targets={targets} d="M188 170l-37 17 9 79 32-33z" />
            <Region id="spinal_erectors" targets={targets} d="M140 184h9v106l-18-8z" />
            <Region id="spinal_erectors" targets={targets} d="M160 184h-9v106l18-8z" />
            <Region id="triceps" targets={targets} d="M82 170c8-7 17-7 23 0l-8 68-22-5z" />
            <Region id="triceps" targets={targets} d="M218 170c-8-7-17-7-23 0l8 68 22-5z" />
            <Region id="forearms" targets={targets} d="M74 239l23 5-24 81-23-5z" />
            <Region id="forearms" targets={targets} d="M226 239l-23 5 24 81 23-5z" />
            <Region id="glutes" targets={targets} d="M108 291l41 4v49l-45-8z" />
            <Region id="glutes" targets={targets} d="M192 291l-41 4v49l45-8z" />
            <Region id="hamstrings" targets={targets} d="M103 345l40 3-12 111-38-3z" />
            <Region id="hamstrings" targets={targets} d="M197 345l-40 3 12 111 38-3z" />
            <Region id="calves" targets={targets} d="M96 458l35 6-8 43-26 0z" />
            <Region id="calves" targets={targets} d="M204 458l-35 6 8 43 26 0z" />
          </g>
          <g data-layer="clothing">
            <path className="avatar__shorts" d="M108 313h84l10 58-44-5-8-26-8 26-44 5z" />
            <path className="avatar__trim" d="M109 318h82M150 319v21" />
          </g>
          <g data-layer="outline">
            <path className="avatar__outline" d="M128 101c-9 14-17 24-35 30-20 9-31 28-36 56L43 325c-3 19 23 24 29 6l17-78 9 118-2 128c-2 20 25 24 31 5l23-130 23 130c6 19 33 15 31-5l-2-128 9-118 17 78c6 18 32 13 29-6l-14-138c-5-28-16-47-36-56-18-6-26-16-35-30" />
            <path className="avatar__outline" d="M150 108v180" />
          </g>
        </g> : null}
      </svg>

      <figcaption className="avatar__caption">
        {targets.length > 0 ? (
          <ul aria-label="Muscles targeted today" className="muscle-targets">
            {targets.map((target) => (
              <li className={`muscle-chip muscle-chip--${target.role}`} key={target.displayName}>
                <span aria-hidden="true" className="muscle-chip__dot" />
                <span>{target.displayName}</span>
                <small>{target.role}</small>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted-copy">Recovery day · no planned targets.</p>
        )}
      </figcaption>
    </figure>
  );
}
