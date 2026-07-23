# LEVELS v2 Implementation Plan

Status: consolidated planning deliverable; feature implementation has not started

Ticket: `LV2-001`

Planning branch: `plan/lv2-001-implementation-plan`

Base: `main` at `bde50c3` (`v0.2.0`)

Prepared: 2026-07-15 (America/Toronto)

## 2026-07-22 post-v2 usability amendment

Status: implemented and locally verified on `feature/workout-flexibility-ui-audit`

This amendment covers a focused usability release after the v2 foundation shipped. It does not
change tenant ownership, migrations, the canonical OpenAPI contract, or generated client. The
existing active-session endpoints already freeze the required interface: add/substitute, patch,
soft-remove, and exact-list reorder all use the session version for optimistic concurrency.

### User outcomes and acceptance criteria

- An in-progress workout exposes one explicit **Edit workout** mode. In that mode the member can
  substitute, add, remove, and move exercises without abandoning or restarting the session.
- Removing an exercise with logged sets requires explicit confirmation and uses the existing
  `confirm_logged_sets` contract. Completed session snapshots remain immutable unless the member
  explicitly resumes the workout through the existing flow.
- Every active-session edit reports success, validation failure, or stale-version conflict in a
  programmatically announced status. A successful write refreshes the authoritative session and
  its version before the next command.
- User-facing weight entry and output use pounds for imperial profiles, including workout sets,
  prior-set summaries, growth increments, records, profile measurements, and load-increment
  settings. API payloads and stored history remain kilograms; conversion is centralized and
  round-trips without cumulative conversion drift.
- Imperial is the default on new registration while metric remains a supported explicit account
  preference. Existing users keep their saved preference.
- The UI audit targets WCAG 2.2 AA: 4.5:1 normal-text contrast, 320 CSS-pixel reflow, visible and
  unobscured keyboard focus, 24-by-24 CSS-pixel minimum pointer targets or sufficient spacing,
  persistent labels/instructions, and programmatically determinable status messages. Workout
  completion dialogs also follow the WAI-ARIA modal-dialog keyboard pattern, including focus
  containment, Escape dismissal, and focus restoration.
- The visual cleanup is intentionally targeted: consolidate weight formatting, simplify the active
  workout hierarchy, make edit actions visually distinct from set logging, normalize control
  height/spacing/focus treatment, and preserve the established dark LEVELS design language.

### Verification and rollout

- Add focused unit tests for unit conversion and each active-session command, including logged-set
  removal confirmation and `409` refresh behavior.
- Update affected feature tests and Playwright coverage for active-workout editing and pounds.
- Run the complete repository gate, record exact results in `VERIFICATION_REPORT_V2.md`, push the
  feature branch, merge through the repository workflow, deploy API/web only after green `main`
  CI, and smoke-check production health plus the authenticated workout journey.

## 1. Authority, scope, and implementation gate

This plan applies the v2 delta in `docs/levels_v2_handoff` to the existing LEVELS v1 repository. Conflicts are resolved in this order:

1. `docs/levels_product_handoff/levels_product_handoff/05_OPENAPI.yaml` after the v2 delta is merged.
2. Alembic migrations, SQLAlchemy models, and `03_ARCHITECTURE_DATA_SECURITY.md`.
3. `02_UX_ACCEPTANCE.md`.
4. `01_PRD_V2.md`.
5. Existing handoff documents and code.

Only this planning file is in scope for `LV2-001`. No application, migration, generated-client, test, deployment, or feature file is changed by this ticket. Implementation may start only after this plan is reviewed and the canonical contract work in `LV2-002` freezes the external names described below.

The v2 release keeps the current React/Vite, Flask/SQLAlchemy/Pydantic, Turso/libSQL, GitHub Pages, and Render topology. OAuth, email verification, password-reset email, teams, social/public profiles, subscriptions, native apps, 3D anatomy, and body-scoring controls remain out of scope.

## 2. Current architecture and implemented feature map

```text
GitHub Pages
  React 18 + TypeScript + Vite + HashRouter
  TanStack Query + generated openapi-fetch client
                  |
                  | JSON / bearer JWT for the configured owner
                  v
Render
  Flask application factory
  Pydantic request DTOs
  feature routes -> services -> repositories
                  |
                  v
Turso/libSQL in production; SQLite locally/tests
```

### Current backend

- Authentication is a single environment-configured username and Argon2 hash. JWT `sub` is the configured username, the role is `owner`, and no database user is loaded.
- The database contains no user/tenant key. Most repositories query all rows or use `LIMIT 1` for the profile.
- Public routes expose the configured owner's dashboard, profile, sessions, records, exercises, splits, water (when visible), and growth data through visibility filters.
- Owner mutations exist for profile/settings, exercises, splits, sessions, set logs, hydration, and export.
- Session start already copies exercise name, variation group, rep range, target RIR, and notes into `session_exercises`; later catalog/template changes do not replace those copied values.
- Set creation, water creation, and session start have idempotency keys, but those keys are globally unique rather than tenant-local. Completion does not persist its idempotency key.
- Export currently iterates every ORM table without tenant filtering. It must not survive unchanged into a multi-account release.
- Seed data is singleton-oriented. It selects the first profile, uses globally stable split/template IDs, and deletes all `exercise_muscles` links before recreating seeded links.
- Alembic has a baseline schema plus water/session idempotency revisions. Empty-database upgrade/downgrade/re-upgrade and metadata drift are tested; populated-v1 upgrade is not.

### Current frontend

- The app shell exposes Today, Journal, Character, Progress, Growth, Splits, Library, and Settings.
- Anonymous users see the real owner's public showcase. Authenticated state is in React memory and disappears on reload.
- Login accepts the configured owner username/password. There is no registration, `/auth/me`, account menu, landing page, or demo mode.
- Today uses `/public/dashboard`; Character uses the same aggregate. Owner controls appear conditionally in those pages.
- Journal supports session start, set logging/editing, exercise substitution, completion/reopen, local drafts, record celebration, and mutation retry safeguards.
- Splits and Library support existing template/catalog management. The present exercise catalog is globally mutable by the owner.
- The avatar is one original Black male inline SVG with front/back views and stable `data-muscle-id` values. It has primary/secondary/stabilizer classes and an accessible target list, but no base choice, appearance settings, per-region focus interaction, or schedule-aware aura.
- The single central `styles.css` is shared by all features; new delegated UI work must use feature-owned style files or be serialized through one owner.

### Current verification baseline

On 2026-07-15, `npm run openapi:check` passed: Redocly validated the canonical v1 contract and the generated TypeScript schema matched it. This is a baseline observation, not v2 verification.

## 3. Canonical OpenAPI changes (`LV2-002`)

The delta file is not a deployable second contract. `LV2-002` will edit only the canonical `05_OPENAPI.yaml`, run Redocly, regenerate `packages/api-client/src/schema.ts`, and commit both together. Generated output will never be edited by hand.

### Global contract changes

- Change the API description from a public single-owner showcase to a private multi-account application with an anonymous read-only demo.
- Remove anonymous access to real-user data. Delete `/public/dashboard` and `/public/profile`; frontend guest browsing uses `/demo/bootstrap` only.
- Every existing user-data read and mutation requires `bearerAuth`: profile/settings, splits, sessions, water, records, growth, export, and available exercise catalog.
- Preserve `/health` as anonymous.
- Use JWT `sub` as a database user ID. No request schema contains `user_id`, `owner_user_id`, `role`, `status`, `token_version`, or `is_demo` as assignable authority.
- Add reusable `403`, `409`, `422`, and `429` response components. Cross-tenant object IDs always use the ordinary `404` response.
- All mutation schemas use `additionalProperties: false`. Security fields are absent rather than accepted and ignored.
- Keep exact-origin CORS behavior; the contract must not imply cookie authentication or wildcard credentials.

### Path and operation map

| Path | Method | Contract decision |
| --- | --- | --- |
| `/auth/register` | POST | Anonymous; `RegisterRequest` -> `201 AuthResponse`; `403` when registration is disabled; `409` generic duplicate conflict; rate-limited. |
| `/auth/login` | POST | Replace username login with `LoginRequestV2`; return `AuthResponse`; unknown email and wrong password share the same `401`. |
| `/auth/me` | GET | Bearer; load active database user and public allow-listed account/profile fields. |
| `/auth/logout` | POST | Bearer; `204`; stateless server is allowed, and the client always clears local state. |
| `/demo/bootstrap` | GET | Anonymous, GET-only fictional aggregate. No demo token is issued. |
| `/me/profile` | GET, PATCH | Replaces `/profile`; bearer and actor-scoped. |
| `/settings` | GET, PATCH | Keep the existing path to minimize churn, but make it actor-scoped and private. Aura preference remains in avatar settings, reduced-motion override remains in app settings. |
| `/me/avatar` | GET, PATCH | Bearer; controlled appearance values only. |
| `/me/streak` | GET | Bearer; deterministic `StreakSummary`. |
| `/today` | GET | Bearer; effective plan aggregate described below. Optional `date` is interpreted in the actor's timezone and is limited to supported planning range. |
| `/today/override` | PUT | Bearer; required `Idempotency-Key`; body includes `expected_version`; returns current `TodayV2`. |
| `/today/override` | DELETE | Bearer; require `local_date` and `expected_version` query parameters so deletion is concurrency-safe; paired swaps delete atomically; `204`. |
| `/today/skip` | POST | Bearer; required `Idempotency-Key`; `advance` or `keep`; returns `TodayV2`. |
| `/today/exercises` | PUT | Bearer; required `Idempotency-Key`; atomically replaces the ordered effective plan for `today_only` or `save_to_split`. |
| `/exercises` | GET | Bearer; available/global/mine scope plus search, muscle, equipment, movement, and measurement filters. |
| `/exercises` | POST | Bearer; creates an actor-owned custom exercise. Global rows cannot be created through member APIs. |
| `/exercises/{id}` | GET | Bearer; global or actor-owned only; another user's custom ID is `404`. |
| `/exercises/{id}` | PATCH, DELETE | Bearer; actor-owned custom rows only. Global mutation is `403`; another user's ID is `404`. Delete remains soft archive. |
| `/splits`, `/splits/{id}`, `/splits/{id}/activate` | Existing methods | Bearer; actor-owned roots and joined children only. |
| `/sessions`, `/sessions/{id}` | Existing methods | Bearer; actor-owned only. Session start requires `Idempotency-Key` and `expected_schedule_version` when starting the effective Today plan. |
| `/sessions/{session_id}/exercises` | POST | Keep existing add/substitute behavior, actor-scope it, and validate available exercise ownership. |
| `/sessions/{session_id}/exercises/{item_id}` | PATCH, DELETE | Add active-session prescription edit/remove. Delete accepts `confirm_logged_sets=true` when logs exist and soft-removes the item. |
| `/sessions/{session_id}/exercises/reorder` | POST | Add exact-list reorder with actor/parent validation and optimistic session update protection. |
| `/sessions/{id}/sets`, `/sets/{id}`, `/sessions/{id}/complete` | Existing methods | Bearer; scope through the actor-owned session. Completion requires `Idempotency-Key`. |
| `/water/today`, `/water/today/undo` | Existing methods | Bearer; actor-local date and actor-local idempotency. |
| `/records`, `/growth/suggestions` | GET | Bearer; actor-owned history only. |
| `/export` | GET | Bearer; actor-owned rows plus safe shared catalog data only; never users/password hashes/demo/other tenants. |

### Exact schema consolidation

The canonical file will add the schemas from `04_OPENAPI_PATCH.yaml` and fully define the two placeholder aggregates. Existing compatible schemas such as `Exercise`, `Split`, `WorkoutSession`, `WaterDay`, `Achievement`, and `MuscleTarget` are reused rather than duplicated.

`AuthResponse` contains `access_token`, `token_type: Bearer`, `expires_in`, and `user: CurrentUser`. `CurrentUser` contains only `id`, `email`, `display_name`, `role`, `timezone`, and `preferred_units`. It never contains password hash, status, token version, or demo state.

`TodayV2` is an object with these required fields:

- `local_date`;
- `user: CurrentUser`;
- `planned_day: SplitDay | null`;
- `effective_day: SplitDay | null`;
- `override: DailyPlanOverride | null`;
- `schedule_version: integer >= 0`;
- `exercise_plan: ExercisePlanItem[]`;
- `active_session: WorkoutSession | null`;
- `muscle_targets: MuscleTarget[]`, preserving primary/secondary/stabilizer roles;
- `water: WaterDay`;
- `latest_achievements: Achievement[]`;
- `avatar: AvatarSettings`;
- `streak: StreakSummary`.

`DailyPlanOverride` contains `id`, `local_date`, `action`, planned/effective split-day IDs, optional swap target date, `schedule_effect`, optional reason, row version, and timestamps. For a skip, `effective_day` and `exercise_plan` are null/empty. For rest, both are null/empty without recording a skip.

`ExercisePlanItem` contains its daily item ID, optional source template item ID, full `Exercise`, sequence, item type, sets, rep/duration/distance prescription, rest, target RIR, superset group, optional flag, and notes. Inputs carry only IDs and editable prescription values.

`DemoBootstrap` is an object with `mode: demo`, a fictional `PublicProfile`, `today` (the demo-safe shape of `TodayV2` without email/account authority), avatar/character data, split summaries, a safe exercise subset, journal samples, progress summaries, and streak. It cannot contain real-user email, private notes, credentials, raw tokens, hidden measurements, internal security fields, or any bootstrap-user identifier.

Appearance strings become explicit enums rather than arbitrary CSS/markup values:

- base: `male | female`;
- skin tone: `deep | rich | medium_deep | medium | light_medium | light`;
- hairstyle: `short_coils | fade | waves | locs | braids | bun | bob | short_straight | covered | bald`;
- hair color: `black | dark_brown | brown | auburn | gray | blonde`;
- outfit: `training_tee | tank_and_shorts | long_sleeve | modest_activewear`;
- palette: `violet | teal | blue | rose | neutral`;
- accessory: `none | glasses | headband | wristbands`;
- background: `none | gradient | gym | dusk`;
- aura style: `standard | rings | sparks`.

Contract review must explicitly confirm that all old anonymous operations were either removed or secured, every operation ID is unique, all `404/409/422/429` cases are present where used, and frontend calls compile only against regenerated output.

## 4. Database migration: expand, backfill, constrain

Migration is split into three ordered Alembic revisions so each responsibility can be tested independently. SQLite/libSQL table rebuilds use Alembic batch operations. No existing row is recreated merely to attach ownership.

### Revision A: expand

1. Create `users` with normalized unique email, Argon2id hash, active/disabled status, member/admin role, token version, demo flag, login timestamp, and normal timestamps.
2. Add nullable `user_id` to all tenant roots listed in the mapping below and nullable `owner_user_id` to `exercises`.
3. Create `schedule_state`, `daily_plan_overrides`, `daily_exercise_plans`, `daily_exercise_plan_items`, `avatar_settings`, and `command_receipts`.
4. Add missing immutable prescription fields to `session_exercises`: planned sets, duration, distance, rest, optional status, item type, and soft-removal timestamp/reason. Existing snapshot fields and IDs remain unchanged.
5. Add new indexes without dropping old uniqueness yet.

`command_receipts` contains `user_id`, operation name, idempotency key, canonical request hash, result resource/version, status, and timestamps, unique on `(user_id, operation, idempotency_key)`. It stores no bearer token or request secret. Schedule commands and session start/complete use it in the same transaction as their mutation.

`daily_exercise_plans` is separate from scheduling overrides because a today-only exercise edit is valid without a replace/swap/rest/skip action. It is unique on `(user_id, local_date)`, records the resolved source split day and version, and owns ordered `daily_exercise_plan_items` with explicit exercise/prescription data.

### Revision B: bootstrap and backfill

1. Before mutating a populated v1 database, require valid `BOOTSTRAP_OWNER_EMAIL` and `BOOTSTRAP_OWNER_PASSWORD_HASH`. Empty databases may upgrade without a bootstrap user so the first account can register normally.
2. Normalize the email by trimming and lowercasing. Create the bootstrap user exactly once using a stable ID derived from the normalized email; reject an email collision with incompatible state.
3. Assign every existing tenant root to that user in place. Preserve every primary key, foreign key, timestamp, completed session, session exercise, set log, record, achievement, suggestion, note, substitution, and visibility setting.
4. Backfill session prescription snapshots from their source template item when present. For rows without a source item, preserve existing snapshot values and use conservative nullable/default prescription values; never derive history from the current catalog after this migration.
5. Initialize the bootstrap `schedule_state` from the existing active split and Toronto/profile local date. Do not manufacture completed or skipped history.
6. Initialize bootstrap avatar settings from the current avatar presentation and safe defaults.
7. Assert before commit that every child resolves to exactly one bootstrap-owned parent and row counts/identity columns match the pre-migration manifest.

The migration test fixture records table counts plus hashes of identity/history columns before upgrade and compares them afterward. A missing bootstrap identity on a populated database must fail with a precise operator error before a partially backfilled state is accepted.

### Revision C: constrain and tenant-local uniqueness

1. Make required root `user_id` columns non-null and add foreign keys to `users.id`.
2. Add required tenant indexes, especially sessions by user/date/status, splits by user/archive/order, water/readiness by user/date, records by user/exercise/type/current, and overrides/plans by user/date.
3. Replace global editable uniqueness with tenant-local constraints:
   - splits: `(user_id, slug)`;
   - readiness: `(user_id, local_date)`;
   - custom exercises: `(owner_user_id, slug)` while global seeded slugs remain uniquely protected;
   - idempotency: tenant + operation/key rather than bare global key;
   - current record lookup/index includes `user_id`.
4. Validate that global exercises (`owner_user_id IS NULL`) are seeded/read-only and custom exercises have an owner.
5. Leave a downgrade that removes only v2 structures when no v2 writes exist. Once multiple accounts or schedule edits exist, rollback is restore-from-branch/backup, not destructive ownership collapse.

### Existing table ownership map

| Existing table | v2 category | Direct column/backfill | Required access rule |
| --- | --- | --- | --- |
| `muscle_groups` | global | none | Shared read-only. |
| `exercises` | mixed global/custom | nullable `owner_user_id`; existing seeded rows remain null | Read global + actor-owned; mutate actor-owned only. |
| `exercise_muscles` | inherited from exercise | none | Global links read-only; custom links accessible only with actor-owned exercise. Seed must not delete custom links. |
| `profiles` | tenant root | `user_id` -> bootstrap | Exactly one per user. |
| `visibility_settings` | profile child | none | Join through actor-owned profile. Public visibility no longer exposes real users. |
| `app_settings` | profile child | none | Join through actor-owned profile; active split must belong to same user. |
| `splits` | tenant root | `user_id` -> bootstrap | All list/get/mutate queries include user. |
| `split_days` | split child | none | Join through actor-owned split. |
| `workout_template_items` | split-day child | none | Join split; referenced exercise must be global or same actor. |
| `template_alternatives` | template child | none | Join split; referenced exercise must be global or same actor. |
| `workout_sessions` | tenant root | `user_id` -> bootstrap | Actor + ID/date/status in query. |
| `session_exercises` | session child | none | Join actor session; exercise may be global or actor-owned. |
| `set_logs` | session-exercise child | none | Join actor session; soft deletes remain tenant-scoped. |
| `readiness_logs` | tenant root | `user_id` -> bootstrap | Unique actor/date. |
| `water_logs` | tenant root | `user_id` -> bootstrap | Actor/date and actor-local idempotency. |
| `personal_records` | tenant root | `user_id` -> bootstrap | Actor query; source set must resolve to same actor when present. |
| `achievements` | tenant root | `user_id` -> bootstrap | Actor query; source set/exercise ownership validated. |
| `progression_suggestions` | tenant root | `user_id` -> bootstrap | Actor query; source session IDs validated before storage/use. |

New `schedule_state`, `daily_plan_overrides`, `daily_exercise_plans`, `avatar_settings`, and `command_receipts` are tenant roots. Their item rows inherit ownership and are always reached through an actor-scoped parent.

## 5. Bootstrap owner, starter accounts, and demo seeding

Global catalog seed and tenant seed become separate transactions/functions.

- Global seed upserts muscle groups, seeded exercises, and only the muscle links belonging to seeded global exercises. It never deletes custom exercise links.
- Registration creates user, profile, visibility, app settings, avatar settings, schedule state, and a clone of starter splits/days/items/alternatives in one transaction. Starter template IDs are new per user; edits cannot affect another user.
- Bootstrap migration assigns existing rows rather than cloning them. Running seed afterward fills only missing defaults and never resets existing owner edits/history.
- Demo seed uses a fixed stable demo user ID, `is_demo=true`, an unusable random/hash-only credential, and fully fictional names, notes, measurements, sessions, records, and dates. It never copies bootstrap rows.
- Demo reseeding is deterministic and idempotent. It may replace only rows whose root belongs to the fixed demo user; it cannot touch normal users.
- `/demo/*` binds the demo actor internally for reads. Normal authenticated mutation services reject `is_demo` before changing state, and no writable demo JWT is issued.
- Production configuration adds `BOOTSTRAP_OWNER_EMAIL`, `BOOTSTRAP_OWNER_PASSWORD_HASH`, and explicit `REGISTRATION_ENABLED`. Production startup fails safe if registration policy or signing configuration is ambiguous.

## 6. Authentication and tenant boundary

Introduce an immutable server-side actor context loaded once per authenticated request:

```python
Actor(user_id, email_normalized, role, token_version, is_demo)
```

JWTs contain `sub=user.id`, `role`, `token_version`, `iat`, `exp`, and `jti`. Token validation loads the user, checks active status and token version, then places the actor in request context. Services receive `actor_user_id` explicitly as their first authority argument; request bodies never supply it.

Repository rules:

1. Tenant root methods require `actor_user_id`; there is no default/current-first-row variant.
2. Direct-object queries filter ID and ownership in the same SQL statement. Missing or foreign IDs both return `404`.
3. Child reads/mutations join through the actor-owned root in the database query; route-level comparisons are not sufficient.
4. Cross-parent attachment validates both parents and referenced custom exercises under the same actor before mutation.
5. Lists, aggregates, record rebuilding, growth computation, Today, and export are scoped at repository/service level, not filtered after serialization.
6. Demo reads use a distinct read-only entry point. Shared member mutation functions reject demo actors defensively.
7. Logs include request ID and safe operation status, not email credentials, authorization headers, tokens, password hashes, or another tenant's content/IDs.

Rate limiting remains by IP plus a non-reversible normalized-email fingerprint. Registration and login use generic responses where enumeration is possible. Passwords are Argon2id, minimum 10 and maximum 256 characters, and paste/password managers remain supported.

## 7. Scheduling state machine

### State and effective-plan precedence

`schedule_state` is one row per user with active split, cursor split day, cursor effective date, and a monotonically increasing version. The version increments once for every accepted scheduling or today-plan mutation.

For an actor/local date, the resolver uses this precedence:

1. an already-started session snapshot for that date;
2. a persisted daily exercise plan;
3. an explicit daily replace/swap/rest/skip override;
4. the cursor-derived planned split day;
5. rest when the date is not a scheduled opportunity.

Today, Character, and session start call this one resolver. They cannot independently calculate a workout.

The cursor anchors the ordered split sequence to the user's configured training opportunities. Before a command, the service deterministically normalizes elapsed opportunities in the actor's timezone. It never uses the API server's local date. An uncompleted elapsed opportunity may break streak calculations but does not create a fake workout.

### Commands and transitions

| Command | Preconditions | Atomic effect |
| --- | --- | --- |
| One-time replace | Target split/day belongs to actor; expected version matches; no conflicting started session | Upsert today's override; cursor unchanged; version +1. |
| Continue from here | Same, selected training day | Upsert today's override; anchor next opportunity to the day after selected; version +1. |
| Swap forward | Target is a future scheduled opportunity and both target days are unresolved | Create two linked override rows exchanging workouts; cursor anchor unchanged; version +1. |
| Rest today | Unresolved today | Upsert one-time rest override; cursor behavior remains unchanged; version +1. |
| Skip and advance | Unresolved scheduled today | Record skip override, advance next opportunity to following split day, mark explicit streak break; version +1. |
| Skip but keep next | Unresolved scheduled today | Record skip override, carry the same planned split day to next opportunity, mark explicit streak break; version +1. |
| Delete override | No session has started from it; expected version matches | Delete single override or both sides of linked swap; restore derived plan; version +1. |
| Start session | Expected schedule version matches | Snapshot the resolved effective plan; one idempotent session; cursor is not double-advanced. |
| Complete session | Actor owns in-progress session | Complete once; advance the corresponding unresolved opportunity once; rebuild actor records; version +1 when schedule advances. |

Every command runs in one database transaction. The service first claims `(actor, operation, idempotency key)` with a canonical request hash. A replay with the same hash returns the recorded result; reuse with different input returns `409`. `expected_version` mismatch returns `409` with the current safe version and no mutation. Unique constraints plus transaction retry handling prevent concurrent skip/start/complete requests from advancing twice.

Swap rows share a `swap_group_id`. The pair is inserted/deleted atomically, and the invariant is that the multiset of the two planned workouts equals the multiset of the two effective workouts.

Streak is computed from scheduled opportunities, completed sessions, and explicit skip/reschedule events. Rest and one-time reschedule do not break it; an explicit skip does. Tiers are exactly none (0-2), subtle (3-6), active (7-13), energized (14-29), and legendary (30+).

## 8. Exercise editing and snapshot rules

- The available picker query returns global plus actor-owned custom exercises only. All combined filters apply in SQL/service logic and cannot reveal another user's custom row.
- `today_only` replaces the actor/date daily plan and items, increments schedule version, and leaves every template row unchanged.
- `save_to_split` performs the same explicit Today plan write and separately reconciles the actor-owned source split day for future sessions. It never updates past sessions or another split/user.
- Session start copies the full effective prescription into `session_exercises`: display name, variation group, planned sets, rep/duration/distance targets, rest, RIR, item type, optional flag, notes, source IDs, and sequence.
- Completed session serialization reads snapshot fields and logged sets, not current template/catalog display values. Catalog archive/rename and later template edits cannot rewrite history.
- Active-session update/substitute changes only that session's snapshot. Reorder validates an exact set of actor-owned session exercise IDs and uses collision-safe two-phase sequencing.
- Removing an active exercise with no logs may soft-remove it directly. If logs exist, the request must explicitly confirm; the session exercise and its logs receive audit-safe soft-removal metadata rather than hard deletion.
- Cross-tenant source template IDs, session item IDs, split day IDs, or custom exercise IDs return `404` and leave the database unchanged.

## 9. Avatar region and component contract

Both male and female bases, front and back, expose the same canonical set of 23 highlightable region IDs:

```text
chest_upper chest_mid chest_lower
delts_front delts_side delts_rear
traps upper_back lats spinal_erectors
biceps brachialis triceps forearms
abs obliques
hip_flexors glutes abductors adductors
quads hamstrings calves
```

One region may use multiple SVG shapes, but every shape uses `data-region-id` from this allow-list. A shared region contract/test compares sets across male/female and asserts front/back union equality. Muscle seed mapping refers only to these IDs; cardiovascular/full-body remain valid accessible labels with no fabricated body region.

Component layers are `AvatarFrame`, `MaleBase`, `FemaleBase`, `FrontView`, `BackView`, `AppearanceLayers`, `MuscleRegions`, `Aura`, `RegionLegend`, and `AccessibleRegionList`. Assets are original repository-owned SVG/React paths; arbitrary uploaded SVG, HTML, URLs, and CSS values are forbidden.

Primary, secondary, and stabilizer roles differ through stroke width/pattern, border/glow, and text/legend in addition to color. One focus/tap target per semantic region announces muscle name and role. The renderer works at 375x812, 390x844, and 1440x900 without horizontal overflow.

Aura tier comes only from the server streak response. User disable suppresses it. `prefers-reduced-motion` or the app override renders a static glow with no pulsing/particles, regardless of aura style.

## 10. Dependency graph and ticket sequence

```text
LV2-001 consolidated plan
  -> LV2-002 canonical OpenAPI + generated client
  -> LV2-101/102/103 users + expand/backfill/constrain migrations
  -> LV2-104 starter/demo seed foundation
  -> LV2-201 database auth + actor context
  -> LV2-202/203 tenant repository conversion + export boundary
  -> LV2-204 isolation matrix
  -> LV2-205 demo API
       -> LV2-206 account/demo frontend
  -> LV2-301..304 scheduling + effective-plan backend
       -> LV2-401..404 exercise-plan/session backend
       -> LV2-305/405 flexible-workout frontend
  -> LV2-501 canonical avatar regions/assets
       -> LV2-504 avatar settings API + Appearance frontend
       -> LV2-505 highlights/accessibility
  -> LV2-601/602 streak service/API
       -> LV2-603 aura frontend
  -> LV2-701 production configuration/rollout
  -> LV2-702 full integration verification
  -> LV2-703 focused read-only reviews and P0 fixes
  -> LV2-704 docs + VERIFICATION_REPORT_V2.md
```

Contract, models, migration, auth core, tenant helpers, seed core, generated client, shared shell, central styles, and E2E spec are serialized ownership areas. Feature agents start only from a commit containing their frozen interfaces.

## 11. Non-overlapping implementation ownership

| Work package | Owner | Exclusive paths while active | May not edit |
| --- | --- | --- | --- |
| Contract | root orchestrator | canonical `05_OPENAPI.yaml`, `packages/api-client/**` | Backend/frontend implementation. |
| Data/auth foundation | root or one foundation implementer, reviewed by root | `models/**`, `migrations/**`, `auth/**`, `config.py`, seed core, migration/auth/seed tests | Web; scheduling feature code. No second agent in these paths. |
| Tenant conversion/demo backend | one backend implementer after foundation | Existing backend feature repositories/services/routes, export, isolation/demo tests | Models/migrations/auth core/OpenAPI/client. |
| Scheduling/exercise backend | one backend implementer after tenant gate | `features/today/**`, `features/sessions/**`, new schedule feature package, their tests | Migration/auth/OpenAPI/generated client; other feature directories. |
| Account/demo frontend | one web implementer after demo contract/API | `App.tsx`, `app/AppShell.tsx`, `auth/**`, new landing/demo/account components and feature-owned styles/tests | Today/Character/Avatar; central generated client. |
| Flexible-workout frontend | one web implementer after schedule API | `features/today/**`, new exercise editor/picker modules and owned tests/styles | App shell/auth/Avatar/Character. |
| Avatar/aura frontend | one avatar implementer after region/API freeze and flexible controls merge | `features/avatar/**`, `features/character/**`, owned assets/styles/tests | App shell/auth/Today/backend/OpenAPI. It imports shared Skip controls; it does not rewrite them. |
| Integration/E2E/docs | root orchestrator, serialized | shared styles/tokens, `e2e/**`, deployment files, README/decisions, verification report | No parallel writer to shared files. |

Each delegated ticket receives only `AGENTS.md`, `00_README_HANDOFF.md`, its relevant handoff files, frozen contract/types, exact owned source paths, acceptance IDs, and narrow commands. Each returns changed files, decisions, exact test results, and unresolved risks. The root reviews every diff before the next dependency is released.

## 12. Verification plan

### Narrow gates during implementation

```powershell
npm run openapi:lint
npm run openapi:generate
npm run openapi:check

uv run --project apps/api pytest apps/api/tests/migrations
uv run --project apps/api pytest apps/api/tests/auth
uv run --project apps/api pytest apps/api/tests/tenant
uv run --project apps/api pytest apps/api/tests/demo
uv run --project apps/api pytest apps/api/tests/schedule
uv run --project apps/api pytest apps/api/tests/exercises apps/api/tests/sessions
uv run --project apps/api pytest apps/api/tests/avatar apps/api/tests/streak

npm --workspace @levels/web run test -- src/auth
npm --workspace @levels/web run test -- src/features/today
npm --workspace @levels/web run test -- src/features/character src/features/avatar
```

Test directories shown above may be created by their owning ticket. Commands must be adjusted only to actual final paths and recorded exactly; no absent test is reported as passed.

### Required test evidence

- Empty, populated-v1, partially seeded, and completed-history migration fixtures; before/after counts, IDs, timestamps, snapshots, sets, records, and relationships.
- Two-user matrix for every private root and child: list/get/create/patch/delete/cross-parent attach, safe `404`, and unchanged foreign state.
- Regression guard against tenant-root repository methods that omit an actor parameter/scope.
- Registration enabled/disabled, normalized duplicate email, Argon2 storage, generic login errors, disabled account, rate limits, token expiry/version, and `/auth/me` allow-list.
- Anonymous demo reads, absent/denied demo writes, fictional payload audit, mutation-service demo guard, deterministic reseed.
- Schedule transition table, timezone boundaries, rest days, paired swap invariant, replay/conflict, and two concurrent skip/start/complete commands.
- Today-only versus save-to-split behavior, global + own exercise selection, foreign custom exercise rejection, snapshot preservation, and logged-set soft removal.
- Male/female front/back region equality, role non-color cues, focus/tap labels, appearance validation, aura tiers, disable setting, and reduced motion.
- Playwright guest demo, new account, migrated owner, two-context isolation, flexible workout, skip/aura, persistence, responsive overflow, browser error/request/5xx, and axe journeys.

### Full clean-checkout release gate

```powershell
npm run bootstrap
npm run openapi:check
npm run lint
npm run typecheck
npm run test
npm run build
npm run e2e
npm run verify
```

`npm run verify` repeats several earlier gates; both the explicit sequence and aggregate command are recorded because the handoff requires exact results. `VERIFICATION_REPORT_V2.md` must identify every command, exit result, environment limitation, and skipped check. A skipped or unavailable check is never called passed.

## 13. Rollout and rollback

1. Create a protected Turso branch/backup and record the current Alembic revision, row counts, and application version without logging private content.
2. Validate bootstrap email/hash and explicit registration policy in a staging clone. Run populated-v1 migration and seed twice; compare integrity manifests.
3. Deploy contract-compatible application code only after the migration/client/tenant test gates pass. Keep exact CORS origins unchanged.
4. Run expand/backfill/constrain through the existing manual production migration workflow with required reviewers; run idempotent global/demo seed.
5. Deploy API, then web. Smoke-check health, bootstrap login/history, a new account, tenant denial, anonymous demo, Today resolution, and mutation denial for demo.
6. Monitor authentication failures, `409` schedule conflicts, migration errors, and 5xx rates without logging credentials or user content.

Before any v2 user writes, application rollback may redeploy v1 while additive columns remain. After new users/schedule/avatar data exist, do not downgrade into the single-owner schema. Roll back by stopping writes, restoring/promoting the pre-release Turso branch/backup, redeploying v1, and restoring the previous web build. Document the expected loss window before production approval.

## 14. Consolidated risk register

| Risk | Severity | Mitigation/release proof |
| --- | --- | --- |
| Existing history or IDs are lost during ownership migration | P0 | In-place backfill, populated fixture manifests, preserved snapshot fields, backup/branch restore drill. |
| Unscoped query/export leaks another tenant | P0 | Direct root ownership, joined child filters, actor-required repositories, full IDOR matrix, export allow-list. |
| Client assigns ownership/role/demo state | P0 | Fields absent from strict schemas; actor comes only from validated JWT/database user. |
| Demo mutates or contains owner data | P0 | Fixed isolated tenant, GET-only route, no demo token, service guard, fictional-payload audit. |
| Concurrent commands double-advance schedule | P0 | Transactional command receipts, request hashes, version check, unique constraints, concurrency tests. |
| Today/Character/session start disagree | P0 | One effective-plan resolver and shared `TodayV2`; session start validates displayed version. |
| Template/catalog edits rewrite completed history | P0 | Full session prescription snapshots and snapshot-only completed serialization tests. |
| Swap-forward loses one workout | P0 | Atomic linked pair and multiset invariant/property tests. |
| Seed deletes custom exercise mappings or resets user edits | P0 | Separate global/tenant seeds scoped by owner and twice-run idempotency tests. |
| OpenAPI/client/backend/frontend drift | P0 | Canonical-first edits, generated-client check, compile gates, contract consistency review. |
| Avatar regions differ across bases or rely only on color | P0 | Shared 23-ID contract, equality/accessibility/visual tests, stroke/pattern/text cues. |
| Scope expands into deferred account/social/3D work | P1 | Ticket allow-lists and acceptance-ID review; defer only documented non-goals. |
| Production rollback collapses new tenants | P0 | No destructive downgrade after v2 writes; restore protected pre-release database branch. |

## 15. Plan review and decisions

This plan has been reviewed against the current contract, ORM tables, migrations, singleton auth, repositories, seed loader, session snapshot implementation, avatar component, frontend shell, tests, and deployment workflow.

Review findings resolved here:

- Data loss: ownership is backfilled on roots without recreating historical rows; session prescriptions are expanded rather than recalculated later.
- IDOR: every current singleton/unscoped repository and the all-table export are explicitly inside the tenant-foundation critical path.
- Race conditions: scheduling, exercise-plan writes, start, and completion share tenant-local command receipts plus optimistic version checks.
- Contract gaps: `TodayV2`, `DemoBootstrap`, concurrency-safe override deletion, session-start versioning, and today-only plan persistence are fully specified before implementation.
- Contract drift: old public-real-user paths are removed rather than left as accidental aliases, and the generated client has one owner.
- Excessive scope: the release remains limited to multi-account privacy/demo, flexible daily plans/exercises, avatar appearance/highlights, streak aura, and the tests/deployment work required to ship them safely.

The next allowed action is `LV2-002`: update the canonical OpenAPI and generated client on a new ticket branch or continuation branch approved by the repository workflow. Bounded implementation agents are not released until that contract and the relevant ownership interfaces are frozen.
