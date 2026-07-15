from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from argon2 import PasswordHasher
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth import require_user
from levels_api.database import get_engine
from levels_api.models import Base, Profile, Split, User, UserRole, UserStatus
from levels_api.seed import seed_user_starter

EMAIL = "brandan@example.com"
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
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            user = User(
                id="00000000-0000-0000-0000-000000000001",
                email_normalized=EMAIL,
                password_hash=password_hash,
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add(user)
            seed_user_starter(session, user, display_name="Brandan Burgess")

    @application.get("/protected-test")
    @require_user
    def protected_test() -> dict[str, str]:
        return {"status": "authorized"}

    yield application
    with application.app_context():
        get_engine().dispose()


def _login(app: Flask, email: str = EMAIL, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return app.test_client().post("/api/v1/auth/login", json={"email": email, "password": password})


def test_valid_credentials_return_member_token_and_current_user(app: Flask) -> None:
    response = _login(app)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 900
    assert payload["user"] == {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": EMAIL,
        "display_name": "Brandan Burgess",
        "role": "member",
        "account_status": "active",
        "timezone": "America/Toronto",
        "preferred_units": "imperial",
    }
    claims = jwt.decode(
        payload["access_token"], JWT_SECRET, algorithms=["HS256"], issuer="levels-api"
    )
    assert claims["sub"] == payload["user"]["id"]
    assert claims["role"] == "member"
    assert claims["ver"] == 0
    assert claims["exp"] - claims["iat"] == 900

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    assert app.test_client().get("/protected-test", headers=headers).status_code == 200
    assert app.test_client().get("/api/v1/auth/me", headers=headers).get_json() == payload["user"]


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "wrong password"), ("missing@example.com", PASSWORD)],
)
def test_invalid_credentials_return_same_generic_error(
    app: Flask, email: str, password: str
) -> None:
    response = _login(app, email, password)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.get_json()["error"]["message"] == "Invalid email or password."


def test_login_is_rate_limited_by_ip_and_normalized_email(app: Flask) -> None:
    for index in range(5):
        email = EMAIL.upper() if index % 2 else EMAIL
        assert _login(app, email=email, password="wrong password").status_code == 401

    limited = _login(app, password="wrong password")
    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "RATE_LIMITED"


def test_missing_invalid_expired_and_disabled_tokens_are_rejected(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/protected-test").status_code == 401
    assert (
        client.get("/protected-test", headers={"Authorization": "Bearer malformed"}).status_code
        == 401
    )

    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "role": "member",
            "ver": 0,
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

    with app.app_context(), Session(get_engine()) as session, session.begin():
        user = session.get(User, "00000000-0000-0000-0000-000000000001")
        assert user is not None
        user.status = UserStatus.DISABLED
    valid_shape = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "role": "member",
            "ver": 0,
            "iss": "levels-api",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "jti": "disabled-test",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get("/protected-test", headers={"Authorization": f"Bearer {valid_shape}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"email": EMAIL, "password": PASSWORD, "extra": True},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": EMAIL, "password": ""},
    ],
)
def test_login_rejects_malformed_payloads(app: Flask, payload: object) -> None:
    response = app.test_client().post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_registration_creates_isolated_starter_account_and_rejects_duplicates(
    app: Flask,
) -> None:
    payload = {
        "email": "New.Member@Example.com",
        "password": "a secure new password",
        "display_name": "New Member",
        "timezone": "Europe/London",
        "preferred_units": "metric",
    }
    response = app.test_client().post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["email"] == "new.member@example.com"
    assert body["user"]["display_name"] == "New Member"
    assert body["user"]["timezone"] == "Europe/London"
    assert body["user"]["preferred_units"] == "metric"

    with app.app_context(), Session(get_engine()) as session:
        new_user = session.scalar(
            select(User).where(User.email_normalized == "new.member@example.com")
        )
        assert new_user is not None
        assert (
            session.scalar(
                select(func.count()).select_from(Profile).where(Profile.user_id == new_user.id)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count()).select_from(Split).where(Split.user_id == new_user.id)
            )
            == 2
        )

    duplicate = app.test_client().post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "ACCOUNT_EXISTS"


def test_logout_revokes_the_presented_token(app: Flask) -> None:
    login = _login(app)
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert app.test_client().post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert app.test_client().get("/protected-test", headers=headers).status_code == 401


def test_registration_can_be_disabled(tmp_path: Path) -> None:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'registration-disabled.db'}",
            registration_enabled=False,
        )
    )
    response = application.test_client().post("/api/v1/auth/register", json={})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "REGISTRATION_DISABLED"
    with application.app_context():
        get_engine().dispose()
