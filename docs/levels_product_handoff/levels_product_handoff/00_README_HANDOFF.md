# LEVELS — Product & Engineering Handoff

**Product:** LEVELS  
**Tagline:** Train. Track. Level up.  
**Owner:** Brandan Burgess  
**Audience:** public read-only visitors; one private administrator.

LEVELS is a public workout showcase and private-admin workout tracker. Visitors can view today's workout, the targeted muscles on an original illustrated avatar, public progress, selected personal records, and public workout history. Only Brandan can sign in and change data.

## Locked stack

- Frontend: React + TypeScript + Vite.
- Styling: centralized design tokens with Tailwind CSS or CSS Modules.
- Avatar: original layered SVG with front/back muscle regions.
- Backend: Flask + Gunicorn.
- Validation and typing: Pydantic, SQLAlchemy 2 `Mapped[...]`, strict TypeScript, generated OpenAPI types.
- Database: Turso/libSQL in production; SQLite-compatible database locally.
- Frontend deployment: GitHub Pages.
- API deployment: Render.
- Testing: Pytest, frontend component tests, Playwright E2E.
- Authentication: one environment-configured admin; no registration.

## Source-of-truth order

1. `05_OPENAPI.yaml`
2. `04_DATA_MODEL.md` and `16_DB_SCHEMA.sql`
3. `06_ACCEPTANCE_CRITERIA.md`
4. `01_PRD.md`
5. Remaining files

Any intentional deviation must be recorded in `DECISIONS_IMPLEMENTED.md`.

## Recommended implementation sequence

1. Plan and lock the repository structure.
2. Establish CI, local commands, and the OpenAPI-generated client.
3. Build typed models, migrations, and idempotent seed data.
4. Build auth and public/admin API boundaries.
5. Build the React shell and design system.
6. Implement Today, Character, Journal, records, Growth, Splits, Library, and Progress.
7. Configure GitHub Pages, Render, and Turso.
8. Run browser-based verification from a clean checkout.

## File index

- `01_PRD.md`: complete product requirements.
- `02_UX_DESIGN_SYSTEM.md`: navigation, colors, avatar and journal design.
- `03_TECHNICAL_ARCHITECTURE.md`: runtime, monorepo, deployment, algorithms.
- `04_DATA_MODEL.md`: typed entities and privacy rules.
- `05_OPENAPI.yaml`: API contract.
- `06_ACCEPTANCE_CRITERIA.md`: release-blocking behavior.
- `07_TEST_AND_QA_PLAN.md`: automated and browser verification.
- `08_AGENT_IMPLEMENTATION_PLAYBOOK.md`: expensive-planner and cheaper-agent workflow.
- `09_CODEX_MASTER_PROMPT.md`: paste-ready implementation prompt.
- `10_BACKLOG.md`: prioritized tickets.
- `11_SECURITY_PRIVACY.md`: threat model and controls.
- `12_DEPLOYMENT_RUNBOOK.md`: provider setup and verification.
- `13_EXERCISE_CATALOG.json`: typed seed catalog.
- `14_SEED_SPLITS.json`: upper/lower and PPL seeds.
- `15_ARCHITECTURE_DECISIONS.md`: accepted choices and alternatives.
- `16_DB_SCHEMA.sql`: SQL implementation reference.
- `17_REFERENCES.md`: official technical references.

- `18_GIT_WORKFLOW.md` — mandatory source-control workflow.
