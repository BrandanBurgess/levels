# LEVELS Architecture Decision Records

## ADR-001 — Static frontend plus separate Flask API

Accepted. GitHub Pages hosts React/Vite; Render runs Flask. This preserves the requested stack because Pages cannot execute Python. Consequences: CORS, two deployments and cold-start handling.

## ADR-002 — Turso instead of a production local SQLite file

Accepted. Render free-service local files are ephemeral. Turso is SQLite-compatible and has Python/SQLAlchemy guidance. Local development remains SQLite-compatible.

Alternatives considered:

- Render Postgres: reasonable but not SQLite-compatible.
- persistent disk: paid and host-coupled.
- Supabase/Neon: good, but Postgres.
- browser-only storage: cannot provide shared persistent public data.

## ADR-003 — SVG avatar for MVP

Accepted. SVG gives direct region mapping, accessibility, low bundle size and easy testing. Three.js is deferred until core flows prove a measurable need.

## ADR-004 — Environment single-admin credential

Accepted. There is one editor, so a user system is unnecessary. No registration/reset. Password rotation occurs through backend environment configuration.

## ADR-005 — OpenAPI-first

Accepted. A language-neutral contract prevents drift between Flask, TypeScript and multiple agents.

## ADR-006 — Metric canonical storage

Accepted: kg, cm, mL, seconds and metres; convert only for display.

## ADR-007 — Excluded hinge-lift variants

Accepted based on explicit owner preference. None appear in seeds or automatic suggestions. Posterior-chain options use hip thrusts, curls, extensions and bridges.

## ADR-008 — Deterministic progression before ML

Accepted. Personal data is small and structured. Rules are explainable and testable.

## ADR-009 — Hash routing default

Proposed default. It avoids project-page refresh 404s. Planner may change only with a tested fallback.

## ADR-010 — Allow-list public serializers

Accepted. Public response models include only intended fields.
