# Browser verification

`npm run e2e` starts an isolated, migrated, seeded SQLite API and a Vite server, then runs the 15 handoff journeys in Chromium. The fixture forces the seeded Upper A plan onto the current Toronto weekday so the suite remains deterministic without changing production time handling.

Playwright uses one worker because the journey intentionally carries workout state through the database. Each browser test receives a fresh context and signs in independently; the access token remains in memory. The committed credential is test-only and is hashed freshly when the temporary API starts.

Traces, screenshots, videos, HTML reports, and temporary databases are ignored locally. CI uploads `playwright-report/` and `test-results/` only when the E2E job fails and retains them for 14 days. Mobile and desktop success screenshots are attached to the report in memory; durable release evidence is captured by LVL-1005.
