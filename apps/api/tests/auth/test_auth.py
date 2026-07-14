from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from argon2 import PasswordHasher
from flask import Flask

from levels_api import Settings, create_app
from levels_api.auth import require_admin
from levels_api.database import get_engine
from levels_api.models import Base, PreferredUnits, Profile

USERNAME = "brandan"
PASSWORD = "correct horse battery staple"
JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture(scope="module")
def password_hash() -> str:
    return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1).hash(PASSWORD)


@pytest.fixture
def app(tmp_path: Path, password_hash: str) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'auth.db'}",
            admin_username=USERNAME,
            admin_password_hash=password_hash,
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                Profile.__table__.insert().values(
                    id="profile-test",
                    display_name="Brandan Burgess",
                    preferred_units=PreferredUnits.IMPERIAL,
                    timezone="America/Toronto",
                    avatar_variant="brandan-original-v1",
                )
            )

    @application.get("/protected-test")
    @require_admin
    def protected_test() -> dict[str, str]:
        return {"status": "authorized"}

    yield application
    with application.app_context():
        get_engine().dispose()


def _login(app: Flask, username: str = USERNAME, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return app.test_client().post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def test_valid_credentials_return_short_lived_owner_token(app: Flask) -> None:
    response = _login(app)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["expires_in_seconds"] == 900
    assert payload["admin"] == {"display_name": "Brandan Burgess"}
    claims = jwt.decode(
        payload["access_token"], JWT_SECRET, algorithms=["HS256"], issuer="levels-api"
    )
    assert claims["sub"] == USERNAME
    assert claims["role"] == "owner"
    assert claims["exp"] - claims["iat"] == 900

    protected = app.test_client().get(
        "/protected-test", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )
    assert protected.status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [(USERNAME, "wrong password"), ("not-the-owner", PASSWORD)],
)
def test_invalid_credentials_return_same_generic_error(
    app: Flask, username: str, password: str
) -> None:
    response = _login(app, username, password)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.get_json()["error"]["message"] == "Invalid username or password."


def test_login_is_rate_limited_by_ip_and_username(app: Flask) -> None:
    for _ in range(5):
        assert _login(app, password="wrong password").status_code == 401

    limited = _login(app, password="wrong password")
    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "RATE_LIMITED"


def test_missing_invalid_and_expired_tokens_are_rejected(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/protected-test").status_code == 401
    assert (
        client.get("/protected-test", headers={"Authorization": "Bearer malformed"}).status_code
        == 401
    )

    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": USERNAME,
            "role": "owner",
            "iss": "levels-api",
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
            "jti": "expired-test",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get("/protected-test", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert "expired" in response.get_json()["error"]["message"].casefold()


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"username": USERNAME, "password": PASSWORD, "extra": True},
        {"username": "", "password": PASSWORD},
        {"username": USERNAME, "password": ""},
    ],
)
def test_login_rejects_malformed_payloads(app: Flask, payload: object) -> None:
    response = app.test_client().post("/api/v1/auth/login", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_no_registration_reset_or_server_logout_routes_exist(app: Flask) -> None:
    client = app.test_client()
    for route in ("register", "reset-password", "logout", "refresh"):
        assert client.post(f"/api/v1/auth/{route}").status_code == 404


def test_unconfigured_authentication_fails_safely(tmp_path: Path) -> None:
    application = create_app(
        Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'unconfigured.db'}")
    )
    response = _login(application)
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "AUTH_NOT_CONFIGURED"
    with application.app_context():
        get_engine().dispose()
