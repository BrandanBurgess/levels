from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'profile.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$unused-in-route-tests",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        from sqlalchemy.orm import Session

        with Session(engine) as session, session.begin():
            seed_session(session)
        token, _ = create_access_token("brandan")
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def test_public_profile_is_anonymous_and_privacy_filtered(app: Flask) -> None:
    response = app.test_client().get("/api/v1/public/profile")

    assert response.status_code == 200
    assert response.get_json() == {
        "display_name": "Brandan Burgess",
        "height_cm": 179,
        "preferred_units": "imperial",
        "timezone": "America/Toronto",
        "avatar_variant": "brandan-original-v1",
    }


def test_owner_profile_requires_auth_and_persists_updates(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/api/v1/profile").status_code == 401

    response = client.patch(
        "/api/v1/profile",
        headers=_auth(app),
        json={
            "display_name": "Brandan B.",
            "height_cm": 180,
            "body_weight_kg": 80.25,
            "preferred_units": "metric",
            "timezone": "UTC",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["body_weight_kg"] == 80.25
    persisted = client.get("/api/v1/profile", headers=_auth(app))
    assert persisted.get_json()["display_name"] == "Brandan B."
    assert persisted.get_json()["timezone"] == "UTC"


def test_settings_update_controls_public_profile_immediately(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/api/v1/settings").status_code == 401

    response = client.patch(
        "/api/v1/settings",
        headers=_auth(app),
        json={
            "default_water_goal_ml": 3200,
            "water_quick_add_ml": [300, 600],
            "default_target_rir": 1.5,
            "default_load_increment_kg": 2.5,
            "visibility": {"show_height": False, "show_body_weight": True},
        },
    )

    assert response.status_code == 200
    assert response.get_json()["default_water_goal_ml"] == 3200
    assert response.get_json()["visibility"]["show_body_weight"] is True
    public = client.get("/api/v1/public/profile").get_json()
    assert "height_cm" not in public
    assert public["body_weight_kg"] == 79.38


def test_active_split_must_exist(app: Flask) -> None:
    response = app.test_client().patch(
        "/api/v1/settings",
        headers=_auth(app),
        json={"active_split_id": "does-not-exist"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["field_errors"] == {
        "active_split_id": "Split does not exist."
    }


@pytest.mark.parametrize(
    ("route", "payload", "field"),
    [
        ("profile", {"height_cm": 99}, "height_cm"),
        ("profile", {"timezone": "Not/A_Timezone"}, "timezone"),
        ("profile", {"unexpected": True}, "unexpected"),
        ("settings", {"default_water_goal_ml": 100}, "default_water_goal_ml"),
        ("settings", {"water_quick_add_ml": []}, "water_quick_add_ml"),
        ("settings", {"visibility": {"show_water": None}}, "show_water"),
    ],
)
def test_invalid_updates_return_field_safe_errors(
    app: Flask, route: str, payload: dict[str, object], field: str
) -> None:
    response = app.test_client().patch(f"/api/v1/{route}", headers=_auth(app), json=payload)

    assert response.status_code == 400
    body = response.get_json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert field in body.get("field_errors", {}) or field in body["message"]
