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
