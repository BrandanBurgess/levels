# Decisions Implemented

This file records implementation decisions and the small, intentional adaptations made after the locked plan. The product handoff remains authoritative.

## Architecture and delivery

1. The browser application is a React 19, TypeScript, and Vite static SPA. `HashRouter` keeps deep navigation compatible with GitHub Pages without requiring a rewrite server.
2. Flask exposes the canonical versioned API below `/api/v1`. A root `/health` alias mirrors `/api/v1/health` solely for Render health checks; it is provider plumbing, not a second product API.
3. SQLAlchemy uses ordinary SQLite locally and in tests, and the libSQL dialect only when a production `libsql://` URL is supplied. Render never relies on its ephemeral filesystem for durable data.
4. The OpenAPI document is the API contract. The TypeScript client is generated deterministically and CI rejects drift.
5. Authentication is deliberately single-owner: an Argon2 password hash and JWT signing key are provider secrets, tokens stay in browser memory, and public DTOs cannot contain owner-only fields.
6. GitHub Actions is the Pages deployment authority. The deploy workflow waits for successful `main` CI and refuses to build without the public `VITE_API_BASE_URL` repository variable.
7. Render is represented by the committed Blueprint and production runbook. Runtime secrets are entered only in Render and are neither committed nor transmitted through the frontend.
8. Production schema changes run through the protected GitHub Actions migration workflow, which requires an explicit confirmation input and scoped Turso environment secrets.

## Product and verification

1. Hydration visibility is owner-controlled. Public responses show only the configured aggregate and never reveal private hydration events.
2. The Journal exposes edit, duplicate, and delete controls for logged sets because the acceptance journey requires correcting a set after creation.
3. Settings exposes the already-modelled week start, reduced-motion preference, water goal, units, public visibility controls, and owner profile fields. This replaced a placeholder discovered during independent verification.
4. Record celebrations are driven by server-confirmed records and deduplicated so retrying or revisiting does not replay the same celebration.
5. Offline Journal writes use idempotency keys and retained drafts; automatic cold-start retries are limited to safe reads.
6. Mobile support is verified at the handoff's 375×812 baseline and an additional iPhone 13 viewport of 390×844. The iPhone journey checks overflow, mobile navigation, settings reachability, browser exceptions, console errors, request failures, and 5xx responses.
7. The committed screenshots contain only public seeded showcase data. Authenticated screenshots and runtime artifacts remain ignored.

## Provider state

GitHub repository configuration was completed through authenticated Git/REST because the active GitHub MCP tool surface was unavailable. Turso MCP is connected but currently lists no databases. Render MCP is not exposed in the active tool registry. These limitations are deployment blockers, not implementation success, and are tracked in `DEPLOYMENT_STATUS.md`.
