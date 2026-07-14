# LEVELS Technical Architecture

## 1. Runtime

```text
Browser
  -> GitHub Pages: React/TypeScript/Vite SPA
  -> HTTPS JSON API
  -> Render: Flask + Gunicorn
  -> SQLAlchemy/libSQL
  -> Turso hosted SQLite-compatible database
```

GitHub Pages is static and cannot run Flask, so the API must be hosted separately.

## 2. Monorepo

```text
levels/
├─ apps/web/
├─ apps/api/
├─ packages/api-client/
├─ docs/
├─ e2e/
├─ scripts/
├─ .github/workflows/
├─ compose.yaml
├─ Makefile
└─ README.md
```

Frontend feature folders: api, components, routes, styles, avatar assets, tests.  
Backend folders: app factory, config, auth, models, schemas, repositories, services, routes, seed and tests.

## 3. Frontend

- React, TypeScript strict, Vite.
- Hash router preferred for GitHub project pages unless a tested SPA fallback is configured.
- TanStack Query or equivalent for server state.
- Zod for validating untrusted responses where useful.
- generated types/client from OpenAPI;
- no duplicated hand-written API types;
- local workout draft in IndexedDB or localStorage;
- token in memory, optionally sessionStorage with documented XSS tradeoff;
- never store password.

Cold-start behavior:

- long enough GET timeout for a sleeping free service;
- visible wake-up state;
- bounded GET retry;
- no automatic retry of POST/PATCH without idempotency key;
- manual retry.

## 4. Backend

- Flask application factory;
- Gunicorn production server;
- SQLAlchemy 2 typed models;
- Pydantic request/response schemas;
- Alembic;
- Pytest;
- structured logs with request IDs;
- CORS allow-list;
- login rate limit;
- centralized typed errors.

Routes handle HTTP. Services own business rules. Repositories own database access. Public/admin schemas are separate.

Error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "field_errors": {"reps": "Must be between 0 and 100."},
    "request_id": "..."
  }
}
```

## 5. Authentication

One admin configured using:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `JWT_SECRET_KEY`

Login verifies the hash and returns a short-lived bearer token. No admin table, registration, reset or OAuth for MVP.

Other environment:

- `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `APP_TIMEZONE=America/Toronto`
- `PUBLIC_WEB_ORIGIN`
- `LOG_LEVEL`

## 6. Database

Production uses Turso/libSQL. Local and tests use SQLite-compatible storage.

Canonical units:

- kg;
- cm;
- mL;
- seconds;
- metres.

Store timestamps in UTC and derive local dates using configured time zone.

Do not store production data in Render local filesystem.

## 7. Contract

- OpenAPI is authoritative.
- Generate frontend types and client.
- CI validates the specification.
- CI fails if generated output is stale.
- Contract tests compare routes and response fields.

## 8. Personal records

Triggered when qualifying sets are created, edited or deleted, and when sessions complete.

Rules:

1. ignore warm-ups by default;
2. determine supported record types;
3. compare against prior values before the set timestamp;
4. update current record;
5. create achievement only on strict improvement;
6. unique idempotency key per set and record type;
7. rebuild affected history after edits/deletes;
8. estimated 1RM is labelled and never used to encourage a max attempt.

## 9. Growth engine

Inputs:

- rep range;
- last three comparable sessions;
- load, reps, RIR, form and pain;
- configured smallest increment;
- readiness if available.

Outputs:

- action enum;
- delta;
- confidence;
- explanation;
- source session IDs.

Core logic:

```text
pain -> no progression
insufficient history -> insufficient data
all sets hit top + acceptable RIR -> smallest load increase
otherwise improved reps -> repeat load
flat -> add one rep target
two declines -> maintain or reduce volume
```

All thresholds are testable and configurable.

## 10. Muscle aggregation

- primary weight seeded 1.0;
- secondary seeded 0.45;
- sum targets across planned items;
- normalize for display;
- preserve accessible exact list;
- mapping test ensures every highlightable muscle has an SVG region.

## 11. CI/CD

Frontend:

- install locked dependencies;
- lint;
- type-check;
- unit test;
- build;
- deploy Pages artifact.

Backend:

- install;
- lint/format check;
- type-check;
- tests;
- migration validation;
- deploy only after checks where possible.

E2E:

- migrate and seed isolated DB;
- start API and web;
- Playwright;
- reports/screenshots on failure.

## 12. Future

- PWA;
- offline sync;
- custom domain;
- always-on backend;
- Three.js spike;
- wearables;
- multiple private users.
