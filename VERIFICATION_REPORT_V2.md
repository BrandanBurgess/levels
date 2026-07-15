# LEVELS v2 Verification Report

Date: 2026-07-15

Branch: `feature/lv2-101-205-tenant-foundation`

Verified implementation commit: `de798bf`

Overall result: **PASS**

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
