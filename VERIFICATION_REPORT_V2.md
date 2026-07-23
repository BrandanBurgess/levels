# LEVELS v2 Verification Report

## Workout flexibility, imperial units, and UI audit follow-up

Date: 2026-07-22

Branch: `feature/workout-flexibility-ui-audit`

Overall result: **PASS — ready for review and deployment through the protected-branch workflow**

### Delivered behavior

- Members can add, substitute, remove, and reorder exercises after a workout has started. Removing
  an exercise that already has logged sets requires explicit confirmation, and stale-version
  conflicts refresh the active session before another edit.
- New accounts default to imperial units. Workout logging, previous sets, records, growth guidance,
  body weight, and load-increment settings render and accept pounds for imperial profiles while the
  API and stored history retain canonical kilograms. Saving a unit preference updates the active
  account context immediately, without requiring a reload.
- A timezone edge case in member starter schedules was fixed so the initial workout is selected
  from the profile's local date rather than the server's UTC date.
- The UI pass normalized control sizing, spacing, contrast, focus visibility, status announcements,
  narrow-screen reflow, reduced motion, and modal keyboard behavior. The acceptance target was
  WCAG 2.2 AA plus the WAI-ARIA Authoring Practices modal-dialog pattern.

### Exact verification results

- `npm run bootstrap`: PASS (7.7 seconds). npm reported two existing high-severity dependency
  advisories; the lockfile was not changed as part of this focused feature.
- `npm run openapi:check`: PASS (9.1 seconds); the canonical contract is valid and the generated
  client has no drift.
- `npm run lint`: PASS (15.1 seconds); web ESLint, API Ruff, and E2E Ruff all passed.
- `npm run typecheck`: PASS (17.1 seconds); web, generated client, and API passed (`84` Python
  source files).
- `npm run test`: PASS (standalone run: 101.7 seconds; repeated by the final aggregate gate): web
  `17/17` files and `80/80` tests, generated client `1/1` file and `2/2` tests, API `144/144` tests.
  Final web coverage was 80.59% statements, 71.99% branches, 78.98% functions, and 85.04% lines;
  API coverage was 92%.
- `npm run build`: PASS (6.1 seconds); production output was 363.39 kB JavaScript and 68.55 kB CSS
  before gzip.
- `npm run e2e`: PASS (27.5 seconds); all `9/9` Playwright acceptance journeys passed, including
  editing an active workout, pound-based set entry, persistence after sign-in, accessibility scans,
  viewport overflow checks, reduced motion, and demo cold-start retry.
- `npm run verify`: PASS (final run: 167.0 seconds); the aggregate gate repeated lint, application and E2E
  type checks (`85` Python/E2E source files), all tests, OpenAPI/client parity, production build, and
  all Playwright journeys successfully.

### Standards references

- [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
- [WCAG target size (minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
- [WCAG focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum)
- [WCAG status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages)
- [WAI-ARIA modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)

Date: 2026-07-15

Branch: `feature/lv2-101-205-tenant-foundation`

Verified implementation commit: `de798bf`

Overall result: **PASS**

## Avatar customization follow-up

Date: 2026-07-16

Branch: `fix/skin-tone-swatch-labels`

Verified implementation commit: `0deee61`

Command: `npm run verify`

Result: PASS (119.2 seconds)

- Web lint, API Ruff, and E2E Ruff: PASS.
- Web, generated client, API, and E2E type checks: PASS.
- Web tests: PASS (`16` files, `69` tests).
- Generated client tests: PASS (`1` file, `2` tests).
- API tests: PASS (`143` tests, `92%` total coverage).
- Canonical OpenAPI lint and generated-client drift check: PASS.
- Vite production build: PASS (`357.94 kB` JavaScript and `63.97 kB` CSS before gzip).
- Playwright: PASS (`9/9` journeys, including registration, sign-in, text-free accessible skin-tone swatches, and persistence of the new avatar options).
- Focused avatar and Character tests: PASS (`14/14`).
- Local visual review: PASS for female long curls and male short locs with a cap; hair frames the skin-filled face and swatch names are not visually rendered.

The follow-up adds `short_locs`, `long_curls`, `curly_bob`, and `cap` to the canonical contract, retains distinct existing long-loc and braid options, and requires no schema migration because avatar choices are stored in existing bounded string columns.

## Full repository gate

Command: `npm run verify`

Result: PASS

Elapsed time: 117.3 seconds

The gate ran, in order:

1. `npm run lint`
   - Web ESLint: PASS
   - API Ruff check and format check: PASS (`107 files already formatted`)
   - E2E Ruff check and format check: PASS
2. `npm run typecheck`
   - Web TypeScript: PASS
   - Generated client TypeScript: PASS
   - API mypy: PASS (`84 source files`)
3. `npm run typecheck:e2e`
   - Playwright TypeScript: PASS
   - API plus E2E mypy: PASS (`85 source files`)
4. `npm run test`
   - Web: PASS (`16` files, `62` tests)
   - Generated client: PASS (`1` file, `2` tests)
   - API: PASS (`136` tests)
   - Web coverage: 78.05% statements, 69.88% branches, 75.82% functions, 83.03% lines
   - API coverage: 92%
5. `npm run openapi:check`
   - Canonical OpenAPI lint: PASS
   - Generated client drift check: PASS
6. `npm run build`
   - TypeScript project build and Vite production build: PASS
   - Production assets: 353.38 kB JavaScript and 62.99 kB CSS before gzip
7. `npm run e2e`
   - Playwright: PASS (`9/9` journeys, 20.7 seconds)

## Acceptance and risk coverage

- Empty database upgrade, downgrade, and re-upgrade pass.
- Populated v1 migration preserves IDs, timestamps, sessions, sets, and snapshots.
- Migration metadata matches the SQLAlchemy model metadata.
- Multi-tenant downgrade aborts before mutation when it cannot be performed safely.
- Deployment seeding creates only the fixed fictional demo tenant; member starter data is created explicitly during registration or test setup.
- Runtime SQLite foreign-key enforcement is verified.
- Tenant isolation covers profiles, splits, sessions and children, hydration, records, growth, export, custom exercises, avatar, settings, and schedule state.
- Cross-tenant object access returns `404`; demo writes return `401` or `405` and change no data.
- Registration enabled/disabled behavior, generic credential failures, registration/login rate limits, JWT status/version validation, and logout invalidation pass.
- Schedule replacement, continue-from-here, swap-forward, skip advance/keep, optimistic concurrency, and idempotent replay pass.
- Active sessions have a database uniqueness invariant; completion CAS conflicts roll back.
- Today-only edits preserve templates; save-to-split retires source rows without changing completed-session payloads.
- Exercise add/remove/reorder/swap, prescription editing, recommended/all selection, and combined filters are covered.
- Male/female front/back avatar regions, non-color target cues, appearance persistence, aura tiers, aura disable, and reduced-motion behavior pass.
- E2E covers anonymous demo safety, registration/login/logout, appearance, flexible Today edits, session completion persistence, Character skip, accessibility, responsive overflow at 375/390/1440 widths, reduced motion, and cold-start retry.

## Non-failing warnings

The API suite emitted 78 warnings: Python 3.13 reported deprecated default SQLite date/datetime adapters in migration fixtures, plus one resource warning for a test SQLite connection during profile settings coverage. These warnings did not affect results and no verification stage failed.

## Final disposition

The canonical OpenAPI, generated client, backend, frontend, migrations, and E2E suite agree. The complete repository verification gate passes with no failing acceptance test.
