# LEVELS deployment

Production uses GitHub Pages for the web app, Render for the Flask API, and Turso for durable data. Secrets belong in provider environment settings and never in Git, workflow output, or frontend variables.

## GitHub Pages

The `Deploy Pages` workflow runs after a successful `CI` workflow on `main` and can also be started manually. It repeats frontend lint, type-check, tests, and build before deployment.

Repository configuration:

1. Set Pages source to **GitHub Actions**.
2. Add the repository variable `VITE_API_BASE_URL` with the deployed Render API URL, including `/api/v1`.
3. Run `Deploy Pages` manually after the Render URL is known, or merge a checked change to `main`.

The project page is built with `VITE_APP_BASE_PATH=/levels/` and uses `HashRouter`, so direct navigation and refresh do not require an SPA fallback. The expected public URL is `https://brandanburgess.github.io/levels/`.

`VITE_API_BASE_URL` is public configuration. Database credentials, JWT signing material, password hashes, and provider tokens must never use a `VITE_` prefix.

## Local production build check

PowerShell:

```powershell
$env:VITE_APP_BASE_PATH = "/levels/"
$env:VITE_API_BASE_URL = "https://api.example.invalid/api/v1"
npm run build
```

The generated `apps/web/dist/index.html` asset paths must begin with `/levels/`. Replace the example API URL only through environment/provider configuration.

## Render

The root [`render.yaml`](../render.yaml) defines one free Python web service in Ohio. It installs the locked API environment with uv, starts the Flask factory under Gunicorn, deploys only after GitHub checks pass, and checks `/health`. The provider health route returns 503 if Turso is unreachable.

Create the service from **Render Dashboard → Blueprints → New Blueprint Instance**, connect `BrandanBurgess/levels`, and apply the root Blueprint. During the initial apply, provide these values only in Render:

- `DATABASE_URL`: the Turso `libsql://` database URL;
- `TURSO_AUTH_TOKEN`: a database token scoped for this service;
- `ADMIN_PASSWORD_HASH`: an Argon2 hash generated locally with `uv run --project apps/api python -m levels_api.scripts.hash_password`.

Render generates `JWT_SECRET_KEY`. Do not replace it with a committed value. The Blueprint supplies the non-secret production mode, Toronto timezone, exact Pages CORS origin, Python version, and uv version.

After the first successful deploy:

1. Record the service’s exact `https://…onrender.com` URL.
2. Verify `/health` returns HTTP 200 with `database: ok`.
3. Set GitHub’s `VITE_API_BASE_URL` repository variable to `<Render URL>/api/v1`.
4. Manually run the `Deploy Pages` workflow.

The live service cannot be created from an unauthenticated checkout. Render must have GitHub repository authorization and the three dashboard-only values above.
