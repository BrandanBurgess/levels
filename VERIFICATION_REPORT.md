# Verification Report

## Verdict

The LEVELS release candidate passes all local implementation, contract, accessibility, responsive-layout, and browser-journey gates. Turso, Render, and GitHub Pages are live and the logged-out production experience passes desktop and iPhone verification. Release tagging remains gated only on repeating the authenticated owner journey against production without exposing its password.

Local verification baseline: candidate `02bf9c62c6130eac9ac3312c86da1c87732ab63b`. Production verification baseline: main `ab5bbd4d0bb92c2bc93c7bf6d30d3256c53c2ef6`. Date: 2026-07-14.

## Clean-checkout commands

The following were run from a separate clean Git worktree with locked dependencies:

| Command | Result |
| --- | --- |
| `make bootstrap` | Pass; npm lock install and complete uv environment sync. |
| `make lint` | Pass; frontend ESLint and backend/e2e Ruff formatting and lint checks. |
| `make typecheck` | Pass; web and generated client TypeScript plus API mypy. |
| `make test` | Pass; 39 web tests, 2 generated-client tests, and 122 API tests. API statement coverage: 96%. |
| `make e2e` | Pass; 16 Playwright journeys in 28.2 seconds. |
| `make verify` | Pass in 113 seconds; lint, application and e2e type checks, all tests, OpenAPI lint/generated-client drift, production build, and all browser journeys. |

The browser run starts from a new SQLite database and applies every Alembic revision before seeding. Separate final-candidate verification also runs migration, seed twice, and database invariant status to prove clean setup and idempotency.

## Browser verification

All required public and owner journeys pass: public privacy, owner login, start workout, set logging, duplicate/edit/delete correction, completion, single record celebration, Progress record display, hydration add/undo, split/settings persistence, logout privacy, cold-start recovery, and reduced-motion behavior.

Responsive and accessibility evidence:

- 375×812: numeric entry remains within the viewport and the mobile navigation is visible.
- iPhone 13 at 390×844: no horizontal overflow; Today, More, and Settings navigation work; settings inputs remain within the viewport; no page exceptions, console errors, failed requests, or 5xx responses occur.
- 1440×900: desktop sidebar is visible and automated axe checks report no critical violations across Today, Character, Journal, Growth, Splits, and Settings.
- Public desktop evidence: `e2e/screenshots/desktop-public-today-1440x900.png`.
- Public iPhone evidence: `e2e/screenshots/iphone-13-public-today.png`.

Live production public verification at https://brandanburgess.github.io/levels/ also passes:

- 1440×900: document and Render dashboard API responses are 200, desktop navigation is visible, horizontal overflow is zero, and there are no critical axe violations, console exceptions, page errors, failed requests, or 5xx responses.
- iPhone 13 at 390×844: document and Render dashboard API responses are 200, mobile navigation is visible, horizontal overflow is zero, and the same browser/network/accessibility audits are clean.
- Live desktop evidence: `e2e/screenshots/live-production-desktop-1440x900.png`.
- Live iPhone evidence: `e2e/screenshots/live-production-iphone13-390x844.png`.

## Security and privacy

- Secret scanning is a protected CI check; `.env`, database files, Playwright artifacts, and authenticated screenshots are ignored.
- The frontend build receives only the public API origin. Turso credentials, the Argon2 hash, and the JWT signing key remain backend/provider secrets.
- Public endpoints are exercised logged out after owner changes and expose only configured fields.
- Mutating endpoints require bearer authentication; CORS is exact-origin configured; auth is rate-limited; exports are owner-only.

## Deployment audit

- GitHub: Pages deployed successfully from main and uses the public Render `/api/v1` origin.
- Turso: `levels-production` is migrated to `a91f6028df36`, seeded, independently count-verified, and delete-protected.
- Render: the service is live; `/health` and `/api/v1/health` return 200 with `database: ok`; public dashboard returns 200.
- CORS: a production preflight from `https://brandanburgess.github.io` returns the exact allowed origin and expected methods/headers.
- Browser: logged-out desktop and iPhone checks pass against the real Pages and Render URLs.
- Pending: authenticated live owner journey and release tag only.

See `DEPLOYMENT_STATUS.md` for the exact actions required to complete production release and the implementation PR links. Final verification PR: https://github.com/BrandanBurgess/levels/pull/50.
