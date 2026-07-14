# LEVELS Multi-Agent Implementation Playbook

## Model allocation

Use the strongest available reasoning model for:

- architecture and plan locking;
- contract and schema review;
- security review;
- integration and release approval.

Use lower-cost coding agents for bounded tickets, tests, components, seeds, documentation and mechanical refactors.

Do not ask a cheaper agent to make open-ended architecture decisions while implementing the full app.

## Roles

### Principal planner

Reads all handoff files and repository. Produces:

- `IMPLEMENTATION_PLAN_LOCKED.md`;
- dependency graph;
- file ownership;
- risk register;
- commands and gates;
- list of human-only provider steps.

It does not implement features during the planning pass.

### Data/contract agent

Owns SQLAlchemy models, migrations, Pydantic, seed import, OpenAPI alignment, conversions and database tests.

### Backend agent

Owns auth, public/admin routes, split/session/water services, PR engine, Growth engine and backend tests.

### Web shell/design agent

Owns Vite/React setup, design tokens, routing, navigation, query client, auth UI, loading/error states.

### Avatar agent

Owns original SVG, region mapping, accessible list and mapping tests. It must not copy a copyrighted character.

### Journal agent

Owns book UI, active session, numeric ergonomics, local draft, set controls, PR celebration and E2E.

### Progress/Growth agent

Owns records, charts, history, deterministic suggestions and filters.

### Split/library agent

Owns split editor, grouping/filtering, alternatives and reorder accessibility.

### Deployment agent

Owns Pages workflow, Render config, Turso setup, health checks and secrets scan.

### Independent QA

Runs clean checkout, all commands and browser journeys; writes `VERIFICATION_REPORT.md`; opens/fixes blockers. Prefer a different context from the main implementer.

## Subagent prompt template

```text
Implement ticket <ID> in LEVELS.

Read:
- docs/00_README_HANDOFF.md
- relevant handoff files
- IMPLEMENTATION_PLAN_LOCKED.md

Scope:
<bounded requirements>

Allowed files:
<paths>

Do not modify:
<contracts/paths>

Acceptance criteria:
<AC IDs>

Verification:
<commands and browser checks>

Rules:
- strict types;
- tests required;
- no TODO placeholders;
- no secrets;
- no OpenAPI drift;
- preserve history;
- smallest coherent change.

At completion report:
1. changed files;
2. commands/results;
3. acceptance evidence;
4. remaining risks.
Do not claim success after a failed check.
```

## Integration order

1. locked plan;
2. foundation/CI;
3. database/OpenAPI;
4. auth/public API;
5. frontend shell/generated client;
6. seed and Today;
7. avatar;
8. journal;
9. records;
10. Growth;
11. splits/library;
12. progress/export;
13. deployment;
14. independent QA;
15. fixes/release.

## Guardrails

- no deadlift seed/suggestion;
- no public mutation;
- no frontend secrets;
- no medical claims;
- no fixed 10%;
- no body rating;
- no copied Nightwing art;
- no historical mutation from template edits;
- no silent contract drift;
- no completion without browser navigation.

## Planner decisions to record

- package manager;
- styling;
- router;
- token storage;
- Python dependency manager;
- Turso connection;
- migration process;
- OpenAPI generation tool;
- chart library;
- local draft storage;
- ID format;
- decimal serialization;
- idempotency;
- wake-up UX;
- CORS;
- Pages base path.

## Cost control

Spend expensive reasoning on initial plan, contract review, security and final integration. Give cheaper agents precise file ownership and acceptance criteria.

## Release artifacts

- `VERIFICATION_REPORT.md`
- `DEPLOYMENT_STATUS.md`
- `DECISIONS_IMPLEMENTED.md`
- root README
- mobile/desktop screenshots
- known limitations
