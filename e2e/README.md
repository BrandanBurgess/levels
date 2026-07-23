# LEVELS v2 browser verification

`npm run e2e` starts an isolated SQLite API and Vite server, then runs the v2 acceptance journeys in Chromium with one worker. The API fixture creates a new temporary directory for every run, applies all Alembic migrations, seeds the global catalog and fictional demo tenant, and provisions a normal member account with a deterministic Lower A schedule cursor. It also adds three completed fixture sessions so streak-aura and reduced-motion checks exercise a visible aura. The temporary database is removed when the API process exits.

The suite covers:

- guest landing, anonymous fictional demo navigation, save prompt, and denied writes;
- registration, starter data, email login, `/auth/me`, logout token invalidation, and a fresh sign-in;
- per-member Appearance persistence across navigation and sign-in;
- Lower-to-Upper Continue from here, two exercise swaps, reorder, and Today-only save;
- starting the effective workout, confirming pound inputs, substituting an exercise mid-session,
  completing it, and verifying it after another sign-in;
- Character Skip with keep-next behavior;
- critical WCAG checks and horizontal-overflow checks at 375×812, 390×844, and 1440×900;
- a static streak aura under `prefers-reduced-motion`;
- GET retry behavior during a simulated API cold start.

The disposable member credentials can be overridden with `LEVELS_E2E_EMAIL` and `LEVELS_E2E_PASSWORD`; defaults use the reserved `.invalid` domain and exist only inside the temporary test database. No production bootstrap identity, password hash, JWT secret, or database is reused. The API creates a fresh random JWT secret at process start.

Useful commands from the repository root:

```bash
npm run typecheck:e2e
npm run lint:e2e
npm run e2e
```

Traces, failure screenshots, videos, HTML reports, and temporary databases remain local/ignored. CI uploads `playwright-report/` and `test-results/` only for failed jobs.
