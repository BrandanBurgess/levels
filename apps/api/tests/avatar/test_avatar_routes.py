from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import AvatarSettings, Base, User, UserRole, UserStatus


@pytest.fixture
def app_and_tokens(tmp_path: Path) -> Iterator[tuple[Flask, str, str]]:
    app = create_app(Settings.for_testing(f"sqlite+pysqlite:///{tmp_path / 'avatar.db'}"))
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as session, session.begin():
            user_a = User(
                id="user-a",
                email_normalized="a@example.com",
                password_hash="$argon2id$fixture",
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            user_b = User(
                id="user-b",
                email_normalized="b@example.com",
                password_hash="$argon2id$fixture",
                status=UserStatus.ACTIVE,
                role=UserRole.MEMBER,
                token_version=0,
                is_demo=False,
            )
            session.add_all([user_a, user_b])
            session.flush()
            session.add_all(
                [
                    AvatarSettings(user_id=user_a.id, outfit_palette="violet"),
                    AvatarSettings(user_id=user_b.id, outfit_palette="teal"),
                ]
            )
        token_a, _ = create_access_token(user_a)
        token_b, _ = create_access_token(user_b)
    yield app, token_a, token_b
    with app.app_context():
        get_engine().dispose()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_avatar_read_and_patch_are_tenant_scoped(
    app_and_tokens: tuple[Flask, str, str],
) -> None:
    app, token_a, token_b = app_and_tokens
    client = app.test_client()
    assert client.get("/api/v1/me/avatar").status_code == 401
    assert (
        client.get("/api/v1/me/avatar", headers=_headers(token_a)).get_json()["outfit_palette"]
        == "violet"
    )

    response = client.patch(
        "/api/v1/me/avatar",
        headers=_headers(token_a),
        json={"base_presentation": "female", "outfit_palette": "rose", "aura_enabled": False},
    )
    assert response.status_code == 200
    assert response.get_json()["base_presentation"] == "female"
    assert response.get_json()["aura_enabled"] is False
    assert (
        client.get("/api/v1/me/avatar", headers=_headers(token_b)).get_json()["outfit_palette"]
        == "teal"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hairstyle", "short_locs"),
        ("hairstyle", "long_curls"),
        ("hairstyle", "curly_bob"),
        ("accessory", "cap"),
    ],
)
def test_avatar_accepts_and_persists_new_customization_options(
    app_and_tokens: tuple[Flask, str, str],
    field: str,
    value: str,
) -> None:
    app, token, _ = app_and_tokens
    client = app.test_client()

    response = client.patch(
        "/api/v1/me/avatar",
        headers=_headers(token),
        json={field: value},
    )

    assert response.status_code == 200
    assert response.get_json()[field] == value
    assert client.get("/api/v1/me/avatar", headers=_headers(token)).get_json()[field] == value


def test_avatar_rejects_uncontrolled_values(
    app_and_tokens: tuple[Flask, str, str],
) -> None:
    app, token, _ = app_and_tokens
    response = app.test_client().patch(
        "/api/v1/me/avatar",
        headers=_headers(token),
        json={"skin_tone": "url(javascript:bad)", "body_score": 99},
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"
