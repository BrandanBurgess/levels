# LEVELS Acceptance Criteria

All P0 criteria are release-blocking.

## Public and auth

- **AC-PUB-01:** A visitor without a token can open Today, Character, public Splits, Library and permitted Progress content.
- **AC-PUB-02:** Any unauthenticated mutation returns 401/403 and changes nothing.
- **AC-PUB-03:** A private session is absent from public lists and returns 404 from a public detail request.
- **AC-AUTH-01:** Valid configured credentials return a short-lived token.
- **AC-AUTH-02:** Invalid credentials return a generic message and are rate-limited.
- **AC-AUTH-03:** No registration or password-reset route exists.
- **AC-AUTH-04:** No secret or password hash appears in the frontend bundle or Git history.

## Character

- **AC-CHAR-01:** The profile displays `Brandan Burgess`.
- **AC-CHAR-02:** Admin can update height and body weight and values persist.
- **AC-CHAR-03:** Every highlightable seeded muscle maps to an SVG region.
- **AC-CHAR-04:** Upper A highlights upper chest, lats/back, delts, biceps and triceps with primary/secondary distinction.
- **AC-CHAR-05:** Front/back views and an accessible text list exist.
- **AC-CHAR-06:** Avatar art is original and contains no copied Nightwing logo, costume or traced art.

## Splits and library

- **AC-SPLIT-01:** Active upper/lower and inactive PPL are seeded.
- **AC-SPLIT-02:** Admin can create, rename, duplicate, reorder, activate and archive a split.
- **AC-SPLIT-03:** Admin can reorder, substitute and remove day items.
- **AC-SPLIT-04:** Template edits do not mutate completed sessions.
- **AC-SPLIT-05:** No deadlift variation is seeded or automatically suggested.
- **AC-LIB-01:** Search matches names and aliases.
- **AC-LIB-02:** Filters support muscle, region, pattern, equipment and unilateral.
- **AC-LIB-03:** Variations group by `variation_group`.
- **AC-LIB-04:** Exercise details show avatar targets.
- **AC-LIB-05:** Seed import is idempotent.

## Journal

- **AC-JRN-01:** Admin starts today's workout from its template.
- **AC-JRN-02:** Exercise substitution preserves template and history.
- **AC-JRN-03:** Load/reps exercise accepts weight, reps, RIR, set type, form and pain.
- **AC-JRN-04:** Duplicate-set and ± increment controls work.
- **AC-JRN-05:** Numeric entry is usable at 375×812 and invokes appropriate keyboards.
- **AC-JRN-06:** Refresh or temporary network loss does not discard the latest local draft.
- **AC-JRN-07:** Completed session follows configured public visibility.

## Personal records

- **AC-PR-01:** A qualifying improvement creates exactly one achievement and current record.
- **AC-PR-02:** Re-saving the same set creates no duplicate achievement.
- **AC-PR-03:** Warm-up sets do not create records by default.
- **AC-PR-04:** Max load, reps-at-load, estimated 1RM and session-volume records work.
- **AC-PR-05:** Journal celebrates only after server confirmation.
- **AC-PR-06:** Historical edit/delete rebuilds affected records.

## Growth

- **AC-GROW-01:** Fewer than two comparable sessions returns insufficient data.
- **AC-GROW-02:** All sets at range top with acceptable RIR may suggest only the smallest increment.
- **AC-GROW-03:** Otherwise the engine may suggest one rep or repeating load.
- **AC-GROW-04:** Pain prevents overload.
- **AC-GROW-05:** Every suggestion cites reasoning and source sessions.
- **AC-GROW-06:** Never suggest fixed 10% or a max single.

## Water

- **AC-WTR-01:** 250/500/750 mL and custom entry work.
- **AC-WTR-02:** Daily totals use configured local time zone.
- **AC-WTR-03:** Undo removes the latest water entry.
- **AC-WTR-04:** Public water appears only when enabled.

## Accessibility and resilience

- **AC-NFR-01:** All core actions are keyboard operable.
- **AC-NFR-02:** Inputs have visible labels and useful errors.
- **AC-NFR-03:** Reduced motion disables confetti and pulsing.
- **AC-NFR-04:** Public shell remains readable during API wake-up.
- **AC-NFR-05:** Automated accessibility suite finds no critical violations.

## Development and deployment

- **AC-DEV-01:** Clean checkout can bootstrap, migrate, seed and run.
- **AC-DEV-02:** lint, type checks, tests and Playwright pass in CI.
- **AC-DEV-03:** OpenAPI validates and generated client is current.
- **AC-DEP-01:** GitHub Actions builds and deploys Pages.
- **AC-DEP-02:** Render Flask connects to Turso and does not depend on local persistence.
- **AC-DEP-03:** Vite base/API URL are correct.
- **AC-DEP-04:** CORS allows only production and approved development origins.
