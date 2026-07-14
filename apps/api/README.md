# LEVELS API

Flask application package for LEVELS. From the repository root:

```powershell
uv sync --project apps/api --all-groups
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api python -m levels_api.seed
uv run --project apps/api flask --app levels_api:create_app run --port 8000 --debug
```

The canonical health route is `GET /api/v1/health`; `GET /health` is the
equivalent provider probe. Local SQLite is the default. Production accepts a
`libsql://` Turso `DATABASE_URL` plus `TURSO_AUTH_TOKEN`. CORS is an exact,
comma-separated origin allow-list and never uses credentialed wildcard access.

Generate the owner password hash locally with a no-echo prompt:

```powershell
uv run --project apps/api python -m levels_api.scripts.hash_password
```

Store only the printed Argon2id hash in `ADMIN_PASSWORD_HASH`. The API exposes
login only; logout clears the in-memory bearer token in the browser.
