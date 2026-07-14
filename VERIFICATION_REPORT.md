# Verification Report

## Verdict

The LEVELS release candidate passes all local implementation, contract, accessibility, responsive-layout, and browser-journey gates. Production release is **not complete** because Turso and Render still require external account input, so no release tag is claimed.

Verification baseline: `main` commit `656bfd06d4f1eaf5ca474059553f9e7e90c455aa`, plus the LVL-1005 verification changes on `test/lvl-1005-independent-verification`. Date: 2026-07-14.

## Clean-checkout commands

The following were run from a separate clean Git worktree with locked dependencies:

| Command | Result |
| --- | --- |
| `make bootstrap` | Pass; npm lock install and complete uv environment sync. |
| `make lint` | Pass; frontend ESLint and backend/e2e Ruff formatting and lint checks. |
| `make typecheck` | Pass; web and generated client TypeScript plus API mypy. |
| `make test` | Pass; 39 web tests, 2 generated-client tests, and 122 API tests. API statement coverage: 96%. |
| `make e2e` | Pass; 16 Playwright journeys in 29.1 seconds. |
| `make verify` | Pending final clean-worktree rerun on the committed verification candidate; this row is updated before merge. |

The browser run starts from a new SQLite database and applies every Alembic revision before seeding. Separate final-candidate verification also runs migration, seed twice, and database invariant status to prove clean setup and idempotency.

## Browser verification

All required public and owner journeys pass: public privacy, owner login, start workout, set logging, duplicate/edit/delete correction, completion, single record celebration, Progress record display, hydration add/undo, split/settings persistence, logout privacy, cold-start recovery, and reduced-motion behavior.

Responsive and accessibility evidence:

- 375×812: numeric entry remains within the viewport and the mobile navigation is visible.
- iPhone 13 at 390×844: no horizontal overflow; Today, More, and Settings navigation work; settings inputs remain within the viewport; no page exceptions, console errors, failed requests, or 5xx responses occur.
- 1440×900: desktop sidebar is visible and automated axe checks report no critical violations across Today, Character, Journal, Growth, Splits, and Settings.
- Public desktop evidence: `e2e/screenshots/desktop-public-today-1440x900.png`.
- Public iPhone evidence: `e2e/screenshots/iphone-13-public-today.png`.

## Security and privacy

- Secret scanning is a protected CI check; `.env`, database files, Playwright artifacts, and authenticated screenshots are ignored.
- The frontend build receives only the public API origin. Turso credentials, the Argon2 hash, and the JWT signing key remain backend/provider secrets.
- Public endpoints are exercised logged out after owner changes and expose only configured fields.
- Mutating endpoints require bearer authentication; CORS is exact-origin configured; auth is rate-limited; exports are owner-only.

## Deployment audit

- GitHub: configuration and required checks are active; Pages is workflow-enabled. Deployment is intentionally gated because no live API origin exists yet.
- Turso: connected MCP returns zero databases. Production database creation is blocked on the account group name and subsequent database-scoped token handling.
- Render: Blueprint is ready, but the active Render MCP tool surface and authorized service are unavailable.
- Live health, live CORS, production migration, live browser, and release-tag checks therefore remain pending and are not reported as passing.

See `DEPLOYMENT_STATUS.md` for the exact actions required to complete production release and the implementation PR links.
