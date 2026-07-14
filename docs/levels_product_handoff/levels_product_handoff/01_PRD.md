# LEVELS Product Requirements Document

## 1. Vision

LEVELS is a polished personal training dashboard that Brandan can publicly share while keeping exclusive editing control. It should feel like a character-progression system rather than a clinical spreadsheet.

The public experience quickly communicates:

- what Brandan is training today;
- which muscles are targeted;
- which split and exercises he uses;
- recent progress and personal records;
- selected workout and conditioning history.

The owner experience makes it quick to:

- start today's planned workout;
- see last performance;
- log sets with few taps;
- substitute exercises without damaging history;
- receive conservative progression suggestions;
- celebrate a real personal best;
- change splits, exercises, privacy, hydration and profile settings.

## 2. Goals

1. Make logging faster than a generic notes app.
2. Create a premium purple-and-black public showcase.
3. Support editable splits, days, exercise alternatives and specialization days.
4. Calculate deterministic, explainable progression suggestions.
5. Celebrate records without requiring risky one-repetition-max tests.
6. Highlight targeted muscles on an original Black male avatar.
7. Stay inexpensive and simple for one owner and modest public traffic.
8. Be fully implementable and verifiable by coding agents.

## 3. Non-goals for v1

- public user accounts, social feeds, comments or leaderboards;
- subscriptions;
- medical, injury, rehabilitation or nutrition advice;
- camera form analysis;
- native mobile apps;
- wearable integrations;
- 3D anatomy;
- direct Nightwing art, logos, costume details or traced copyrighted assets.

## 4. Roles

### Public viewer

Can view public pages and public-safe data without a login.

Cannot mutate anything or see private notes, hidden metrics, draft sessions, credentials or admin controls.

### Admin owner

Brandan is the only administrator. Admin can:

- edit profile and privacy;
- create, duplicate, activate, reorder and archive splits;
- edit day templates and alternatives;
- manage exercises and muscle mappings;
- start, edit, complete and delete workouts;
- log sets, hydration, readiness, conditioning and notes;
- export data and rebuild records.

No registration or password-reset endpoint exists in v1.

## 5. Tabs

### Today

- current Toronto-local date;
- scheduled day or rest/optional day;
- original avatar with primary and secondary muscles highlighted;
- planned exercise summary;
- water meter;
- latest public achievement;
- admin-only readiness and `Start workout`;
- graceful backend wake-up state.

### Character

- original cartoon-style Black male avatar;
- short dreadlocks to approximately mouth level;
- name `Brandan Burgess`;
- front/back toggle;
- neutral and highlighted states;
- admin height and body-weight controls;
- independent public visibility for height and weight;
- accessible text list of targeted muscles.

The avatar must be neutral. No attractiveness score, ideal-body comparison, body-fat guess or negative body messaging.

### Workout Journal

Visual style: an open workout book with dark leather/purple framing, warm paper, subtle ruled lines and high-contrast ink.

Admin features:

- start from today's template or choose another day;
- substitute an exercise while preserving template and history;
- add an exercise;
- show previous comparable performance;
- log weight, reps, RIR, time, distance or rounds as appropriate;
- set type: warm-up, working, back-off, drop or failure;
- duplicate previous set;
- fast ± weight and rep controls;
- mobile numeric keyboard;
- local draft and remote autosave;
- private and public notes;
- complete or resume session.

Public viewers see only completed sessions at the configured visibility level.

### Progress

- personal records;
- exercise history;
- best load by rep range;
- estimated 1RM trend, explicitly labelled as an estimate;
- volume trends where meaningful;
- consistency calendar using neutral, non-shaming language;
- filters by exercise, muscle, day and date;
- JSON/CSV export for admin.

Record types:

1. heaviest working set;
2. most reps at a load;
3. estimated 1RM;
4. highest exercise session volume;
5. best time, distance or rounds for conditioning.

### Growth

A fixed 10% improvement every day is itself exponential and is not a realistic workout rule. The app instead makes small, explainable suggestions.

Priority rules:

1. If all working sets reach the top of the range with acceptable RIR and form, suggest the smallest configured load increment.
2. Otherwise suggest one additional rep, repeating the load, or matching prior performance.
3. If performance has declined, suggest maintenance or reduced volume.
4. If pain or poor form is logged, do not recommend overload.
5. Never suggest a maximal single or a fixed 10% load jump.
6. Show the recent sessions and reasoning behind each suggestion.

Example outputs:

- `Add one rep to set 3`
- `Repeat 70 lb and make all three sets consistent`
- `Increase by 2.5 lb`
- `Maintain today`
- `Use the easier variation`
- `Not enough history yet`

### Splits & Exercise Library

Split features:

- active split;
- create, rename, duplicate, reorder, activate and archive;
- add/remove/reorder days;
- day types: upper, lower, push, pull, legs, conditioning, specialization, rest;
- alternatives per exercise slot;
- default sets, range, rest and notes;
- seeded upper/lower and PPL.

Exercise library:

- search names and aliases;
- filter by primary/secondary muscle, region, pattern, equipment and unilateral status;
- group overlapping variants using `variation_group`;
- preview avatar highlights;
- include common machine, cable, dumbbell, barbell, bodyweight and conditioning movements used in bodybuilding-style routines;
- exclude all deadlift variants from seeds and automatic suggestions.

### Settings

Admin-only:

- profile, units and time zone;
- water goal and quick-add amounts;
- active split and week start;
- privacy for height, body weight, water, sessions, sets, notes, records, charts and readiness;
- load increments;
- reduced motion;
- export;
- logout.

## 6. Seed program

Active split: four-day upper/lower plus optional day.

- Upper A: incline press and back.
- Lower A: squat, hips and unilateral legs.
- Upper B: overhead press, lats, delts and arms.
- Lower B: jumps, squat/leg press pattern, hip extension, hamstrings, calves and core.
- Optional: conditioning or shoulders/arms, chest or back specialization.

Owner preference:

- main work generally 5–8;
- secondary work generally 6–10;
- isolation may use 8–15;
- `8` is the convenient default target;
- hard but controlled sets, generally 1–2 reps in reserve;
- short cardio activation before lifting and harder conditioning after lifting or on the optional day.

No conventional, Romanian, stiff-leg, sumo or trap-bar deadlift in seeds.

## 7. Water tracking

- canonical unit: mL;
- user-configured target;
- optional estimate but no claim that height and weight determine a precise medical target;
- seeded quick-add: 250, 500 and 750 mL;
- custom amount;
- undo most recent entry;
- local-day aggregation;
- public visibility toggle;
- no dehydration diagnosis or medical warnings.

## 8. Readiness and conditioning

Optional daily readiness:

- energy 1–5;
- soreness 1–5;
- sleep quality 1–5;
- pain flag;
- private note.

Conditioning supports duration, rounds and distance. Pre-lift cardio is easy activation; hard finishers occur after lifting or on optional day. The app must not reward dangerous exhaustion.

## 9. Public privacy

Visibility modes:

- session hidden, summary or full;
- notes private by default;
- water, body weight, height, records and charts independently controlled.

Public responses must be created using allow-list response models rather than serializing full database objects and deleting fields.

## 10. Functional requirements

- Public pages work without auth.
- Only admin can mutate.
- Admin credentials persist only on backend.
- Split edits persist across refresh.
- Historical sessions do not change when a template changes.
- Personal records recalculate idempotently.
- Muscle highlights are aggregated from exercise mappings.
- Growth suggestions are deterministic and tested.
- Water aggregates by configured local date.
- Variations are grouped.
- Admin can export data.

## 11. Non-functional requirements

- mobile-first at 375 CSS px;
- polished desktop showcase;
- WCAG 2.2 AA target;
- reduced-motion support;
- strict TypeScript with no unchecked `any`;
- typed SQLAlchemy and Pydantic models;
- migrations committed;
- consistent error envelope;
- friendly Render cold-start handling;
- secrets never present in static assets;
- UTC storage and Toronto-local daily grouping by default.

## 12. MVP success

- A workout can be logged faster than in a generic notes app.
- A visitor understands today's target within ten seconds.
- A record creates one correct celebration.
- The app deploys from GitHub using documented steps.
- A new agent can run it locally from a clean checkout.
