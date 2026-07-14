# LEVELS

LEVELS is a public workout showcase and private single-owner training tracker. The production topology is a React/Vite site on GitHub Pages, a Flask/Gunicorn API on Render, and a Turso Cloud database.

The product contract and requirements live in [`docs/levels_product_handoff/levels_product_handoff`](docs/levels_product_handoff/levels_product_handoff). The locked delivery sequence is in [`IMPLEMENTATION_PLAN_LOCKED.md`](IMPLEMENTATION_PLAN_LOCKED.md).

## Prerequisites

- Node.js 22.12 or newer and npm 10 or newer
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- GNU Make (optional wrapper; every command also has an npm equivalent)
- Docker with a running daemon (optional Compose workflow)

## Clean checkout

```powershell
git clone https://github.com/BrandanBurgess/levels.git
cd levels
Copy-Item .env.example .env
npm run bootstrap
npm run dev
```

Open `http://localhost:5173`. The API runs at `http://localhost:8000`.

Before admin login is implemented, keep the placeholder secret values in local development only. Never commit `.env`. The later auth ticket provides a no-echo password hash generator.

## Commands

| Goal | Cross-platform command | Make wrapper |
| --- | --- | --- |
| Install locked dependencies | `npm run bootstrap` | `make bootstrap` |
| Run API and web | `npm run dev` | `make dev` |
| Lint | `npm run lint` | `make lint` |
| Type-check | `npm run typecheck` | `make typecheck` |
| Unit/integration tests | `npm run test` | `make test` |
| Build frontend | `npm run build` | `make build` |
| Seed database | `npm run seed` | `make seed` |
| Browser tests | `npm run e2e` | `make e2e` |
| Full local gate | `npm run verify` | `make verify` |

`make e2e` becomes a real Playwright journey in LVL-1004. Database migrations and seeding are introduced by LVL-102 and LVL-103.

## Optional Compose workflow

With Docker Desktop or another Docker daemon running:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Compose persists the local SQLite database in a named volume. Production never uses a Render-local database file.

## Repository layout

- `apps/web`: React/TypeScript/Vite frontend
- `apps/api`: Flask Python package
- `packages/api-client`: generated OpenAPI client package (LVL-104)
- `e2e`: Playwright journeys (LVL-1004)
- `scripts`: repository automation
- `.github/workflows`: CI and deployments (LVL-003 onward)

## Production deployment

Provider configuration and the Pages workflow contract are documented in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). The frontend deploys only after successful `main` CI and requires the public `VITE_API_BASE_URL` repository variable; backend and database secrets never enter the frontend build.

## Git workflow

All work follows `docs/levels_product_handoff/levels_product_handoff/18_GIT_WORKFLOW.md`: one ticket branch, Conventional Commits, pull request, required checks, squash merge, and branch deletion. Do not work directly on `main`.
