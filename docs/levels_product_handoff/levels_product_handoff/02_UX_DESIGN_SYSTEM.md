# LEVELS UX and Design System

## Brand

LEVELS should feel athletic, focused, premium and game-like. Use dark surfaces, multiple purple shades and restrained motion. Avoid neon clutter, body-shaming copy and copied comic-book branding.

## Color tokens

```css
:root {
  --bg-0: #07050b;
  --bg-1: #0e0915;
  --surface-1: #171020;
  --surface-2: #21152f;
  --surface-3: #2b193d;
  --purple-950: #210735;
  --purple-850: #38105a;
  --purple-700: #5b1fa6;
  --purple-600: #7430d7;
  --purple-500: #8b3dff;
  --purple-400: #a866ff;
  --purple-300: #c49aff;
  --purple-150: #e3ceff;
  --text-strong: #f8f4ff;
  --text: #e7dcf3;
  --text-muted: #bbaac9;
  --black-ink: #100b13;
  --paper: #f3eadb;
  --paper-line: #cdb7db;
  --success: #76dfa6;
  --warning: #f0c96d;
  --danger: #ff7e92;
  --focus: #d8b7ff;
}
```

Use near-white text on dark surfaces. Use black ink only on paper/light lavender. All combinations must pass contrast checks.

## Navigation

Mobile bottom tabs:

- Today
- Journal
- Character
- Progress
- More

More includes Growth, Splits, Library and Settings.

Desktop uses a left rail, center content and optional right rail for water, latest PR and readiness.

## Today layout

- date and workout title;
- central avatar;
- muscle legend;
- planned exercise list;
- water and latest achievement;
- admin actions appear without disrupting the public showcase.

When the API is sleeping, show `Waking up your training data…`, preserve the static shell and retry bounded GET requests.

## Character

- front/back segmented control;
- visible height/weight labels;
- admin sliders plus direct numeric entry;
- primary muscle glow: brighter purple;
- secondary muscle glow: darker purple;
- accessible muscle list outside SVG;
- subtle full-body aura for conditioning, removed under reduced motion.

The sliders must not rate the body or simulate an “ideal” physique.

## Journal

Desktop: open two-page book.  
Mobile: one paper page with sticky set-entry controls.

Requirements:

- 48 px target controls;
- `inputmode=decimal` for load;
- `inputmode=numeric` for reps/time/water;
- duplicate previous set;
- load ± configured increment;
- reps ±1;
- clear save status;
- add-set button remains reachable above mobile keyboard;
- paper texture never reduces readability.

## Growth

Suggestion card:

- exercise;
- suggested action;
- confidence;
- recent evidence;
- recovery constraint when relevant;
- `Use suggestion` for admin.

No pseudo-scientific “fitness score”.

## Splits and Library

- cards with drag handles and keyboard reorder buttons;
- grouped variants;
- filter chips;
- avatar preview;
- alternatives visible before selection.

## Avatar specification

Use original layered SVG, not Three.js for MVP.

Required front/back regions:

- chest_upper, chest_mid, chest_lower;
- delts_front, delts_side, delts_rear;
- lats, upper_back, traps;
- biceps, triceps, forearms;
- abs, obliques;
- glutes, quads, hamstrings, calves.

Hair, skin, clothing, outline and highlights are separate layers. Stable `data-muscle-id` values drive highlighting.

Why SVG:

- precise muscle selection;
- small bundle;
- testable mapping;
- responsive;
- keyboard and screen-reader support;
- no 3D modelling/rigging cost.

Three.js is a post-MVP experiment only.

## Motion

Allowed:

- 150–250 ms fades;
- water-level easing;
- brief PR confetti under two seconds;
- low-amplitude muscle pulse;
- subtle page-turn hint.

Disallowed:

- flashing;
- infinite high-motion backgrounds;
- delayed inputs;
- required gestures.

## Copy

Use:

- `Ready for Upper A`
- `Last time: 70 lb × 8`
- `New rep record`
- `Maintain today`
- `Not enough history yet`

Avoid:

- `Weak`
- `No excuses`
- `Punishment`
- `Perfect body`
- `You failed`
- `10% stronger today`

## Accessibility

- visible labels;
- useful field errors;
- logical focus;
- keyboard reorder alternative;
- text summaries for charts and avatar;
- no color-only states;
- reduced motion;
- 200% zoom support.
