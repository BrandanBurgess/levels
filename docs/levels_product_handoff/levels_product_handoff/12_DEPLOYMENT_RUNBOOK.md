# LEVELS Deployment Runbook

## Topology

- React/Vite: GitHub Pages.
- Flask/Gunicorn: Render.
- Database: Turso.
- CI: GitHub Actions.

## Human prerequisites

Create/authorize GitHub repo, Render service, Turso database and repository/provider secrets. Agents must not invent or print real secrets.

## Local env example

API:

```text
DATABASE_URL=sqlite:///./levels-dev.db
ADMIN_USERNAME=brandan
ADMIN_PASSWORD_HASH=<generated>
JWT_SECRET_KEY=<random>
CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_TIMEZONE=America/Toronto
```

Web:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_BASE_PATH=/
```

## Turso

1. Authenticate CLI.
2. Create DB.
3. obtain URL/token.
4. add to Render env.
5. run migrations.
6. run idempotent seed.
7. verify health and public read.

Never commit production data or token.

## Render

- backend root directory;
- locked dependency build;
- Gunicorn start command;
- `/health`;
- deploy after CI where possible;
- production debug off;
- env vars in dashboard.

Free service may sleep and local filesystem is ephemeral. The frontend must show wake-up state and all persistence must be remote.

## GitHub Pages

- Vite `base=/<repo>/` for project page;
- `base=/` for user page/custom domain;
- hash router preferred;
- Pages source: GitHub Actions.

Workflow:

1. install;
2. lint;
3. type-check;
4. test;
5. build;
6. upload artifact;
7. deploy.

API URL is public configuration, not secret.

## CORS

Allow exact Pages origin, optional custom domain and approved local origins only outside production.

## Migrations

Preferred MVP: protected/manual migration workflow before backend deploy. Avoid multiple Gunicorn workers racing migrations.

## Admin password

Provide:

```bash
python -m levels_api.scripts.hash_password
```

Prompt with no echo, confirm, print only hash.

## Post-deploy verification

1. `/health`;
2. public Today in private browser;
3. wake-up state;
4. admin login;
5. water add/undo;
6. start workout;
7. log/delete test set;
8. inspect source/network for secrets;
9. CORS;
10. refresh navigation;
11. mobile layout;
12. remove/private test data.

## Rollback

Frontend: redeploy prior artifact/commit.  
Backend: deploy prior compatible commit.  
Database: export before risky migrations and prefer forward fixes.

## Custom domain later

Update Vite base, CORS, public origin and HTTPS.


## 13. GitHub repository protections

Before public development begins:

1. Protect `main`.
2. Require pull requests.
3. Require CI status checks.
4. Block force pushes.
5. Require conversation resolution.
6. Prefer linear history and squash merging.
7. Configure automatic deletion of merged branches.
8. Add the pull-request template described in `18_GIT_WORKFLOW.md`.

Use GitHub MCP to configure these settings when the connected token has administration permission. Record any setting that still requires the repository owner.
