from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from flask import Flask

from levels_api import Settings, create_app
from levels_api.config import ConfigurationError
from levels_api.database import engine_configuration, get_db, get_engine
from levels_api.errors import ApiError
from levels_api.logging import JsonFormatter


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'platform.db'}"))
    yield application
    with application.app_context():
        get_engine().dispose()


def test_health_routes_share_contract_safe_payload(app: Flask) -> None:
    client = app.test_client()

    api_response = client.get("/api/v1/health")
    provider_response = client.get("/health")

    assert api_response.status_code == 200
    assert api_response.get_json() == {
        "status": "ok",
        "version": "0.1.0",
        "database": "ok",
    }
    assert provider_response.get_json() == api_response.get_json()


def test_health_reports_degraded_database_without_leaking_details(tmp_path: Path) -> None:
    app = create_app(
        Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'missing' / 'db.sqlite'}")
    )

    response = app.test_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "version": "0.1.0",
        "database": "degraded",
    }
    provider = app.test_client().get("/health")
    assert provider.status_code == 503
    assert provider.get_json()["database"] == "degraded"


def test_request_ids_are_validated_and_added_to_errors(app: Flask) -> None:
    requested_id = str(uuid4())
    response = app.test_client().get("/missing", headers={"X-Request-ID": requested_id})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == requested_id
    assert response.get_json()["error"]["request_id"] == requested_id

    generated = app.test_client().get(
        "/missing", headers={"X-Request-ID": "not-a-valid-request-id"}
    )
    assert UUID(generated.headers["X-Request-ID"])
    assert "not-a-valid-request-id" not in generated.get_data(as_text=True)


def test_api_errors_use_central_envelope(app: Flask) -> None:
    @app.get("/validation-example")
    def validation_example() -> None:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "One or more fields are invalid.",
            {"reps": "Must be between 0 and 100."},
        )

    response = app.test_client().get("/validation-example")

    assert response.status_code == 422
    assert response.get_json()["error"] | {"request_id": "ignored"} == {
        "code": "VALIDATION_ERROR",
        "message": "One or more fields are invalid.",
        "field_errors": {"reps": "Must be between 0 and 100."},
        "request_id": "ignored",
    }


def test_unexpected_errors_do_not_expose_stack_or_exception(app: Flask) -> None:
    @app.get("/failure-example")
    def failure_example() -> None:
        raise RuntimeError("private database detail")

    response = app.test_client().get("/failure-example")

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "private database detail" not in response.get_data(as_text=True)


def test_cors_uses_exact_allowlist_without_credentials(app: Flask) -> None:
    client = app.test_client()
    allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    denied = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Authorization" in allowed.headers["Access-Control-Allow-Headers"]
    assert "Access-Control-Allow-Credentials" not in allowed.headers
    assert "Access-Control-Allow-Origin" not in denied.headers

    preflight = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_database_session_is_request_scoped(app: Flask) -> None:
    sessions: list[int] = []

    @app.get("/session-example")
    def session_example() -> dict[str, str]:
        sessions.append(id(get_db()))
        assert get_db() is get_db()
        return {"status": "ok"}

    client = app.test_client()
    client.get("/session-example")
    client.get("/session-example")
    assert len(set(sessions)) == 2


def test_libsql_urls_are_configured_for_secure_turso_connections() -> None:
    url, connect_args = engine_configuration("libsql://levels-example.turso.io", "test-token")

    assert url == "sqlite+libsql://levels-example.turso.io?secure=true"
    assert connect_args == {"auth_token": "test-token"}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"CORS_ALLOWED_ORIGINS": "*"}, "Invalid CORS origin"),
        (
            {"CORS_ALLOWED_ORIGINS": "https://levels.example/path"},
            "exact origins",
        ),
        (
            {"DATABASE_URL": "libsql://levels.turso.io"},
            "TURSO_AUTH_TOKEN is required",
        ),
        ({"LOG_LEVEL": "LOUD"}, "Invalid LOG_LEVEL"),
    ],
)
def test_unsafe_configuration_fails_closed(overrides: dict[str, str], message: str) -> None:
    values = {
        "APP_ENV": "production",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "CORS_ALLOWED_ORIGINS": "https://levels.example",
        "PUBLIC_WEB_ORIGIN": "https://levels.example",
        "ADMIN_USERNAME": "owner",
        "ADMIN_PASSWORD_HASH": "$argon2id$test-placeholder",
        "JWT_SECRET_KEY": "test-only-key-with-at-least-32-characters",
        **overrides,
    }
    with pytest.raises(ConfigurationError, match=message):
        Settings.from_mapping(values)


def test_json_formatter_emits_machine_readable_context() -> None:
    import logging

    record = logging.LogRecord("levels", logging.INFO, __file__, 1, "ready", (), None)
    record.request_id = "request-1"
    record.method = "GET"
    record.status = 200
    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "ready"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "request-1"
    assert payload["method"] == "GET"
    assert payload["status"] == 200
