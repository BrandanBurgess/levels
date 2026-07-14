from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.orm import Session

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
            f"sqlite+pysqlite:///{tmp_path / 'exercises.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$unused-in-route-tests",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            seed_session(session)
        token, _ = create_access_token("brandan")
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def _write(slug: str = "custom_press") -> dict[str, object]:
    return {
        "name": "Custom Press",
        "slug": slug,
        "aliases": ["my press"],
        "variation_group": "custom_press",
        "movement_pattern": "horizontal_push",
        "equipment": "cable",
        "measurement_type": "load_reps",
        "compound": True,
        "unilateral": False,
        "default_rep_min": 6,
        "default_rep_max": 10,
        "default_rest_seconds": 90,
        "automatic_progression_enabled": True,
        "muscle_targets": [
            {
                "slug": "upper_chest",
                "display_name": "Upper Chest",
                "role": "primary",
                "intensity": 1,
                "svg_region_ids": ["chest_upper"],
            }
        ],
    }


def test_search_matches_aliases_and_returns_group_and_avatar_targets(app: Flask) -> None:
    response = app.test_client().get("/api/v1/exercises?q=crossover")

    assert response.status_code == 200
    exercises = response.get_json()
    assert [exercise["id"] for exercise in exercises] == ["cable_fly"]
    assert exercises[0]["variation_group"] == "chest_fly"
    assert exercises[0]["muscle_targets"][0]["svg_region_ids"]


def test_filters_cover_muscles_region_pattern_equipment_and_laterality(app: Flask) -> None:
    response = app.test_client().get(
        "/api/v1/exercises?primary_muscle=upper_chest&secondary_muscle=triceps"
        "&body_region=chest&movement_pattern=horizontal_push&equipment=barbell&unilateral=false"
    )

    assert response.status_code == 200
    exercises = response.get_json()
    assert {exercise["id"] for exercise in exercises} == {"incline_barbell_bench_press"}


def test_detail_and_missing_exercise(app: Flask) -> None:
    client = app.test_client()
    detail = client.get("/api/v1/exercises/pull_up")
    missing = client.get("/api/v1/exercises/not-real")

    assert detail.status_code == 200
    assert detail.get_json()["name"] == "Pull-Up"
    assert missing.status_code == 404


def test_writes_require_authentication(app: Flask) -> None:
    client = app.test_client()

    assert client.post("/api/v1/exercises", json=_write()).status_code == 401
    assert client.patch("/api/v1/exercises/pull_up", json=_write()).status_code == 401
    assert client.delete("/api/v1/exercises/pull_up").status_code == 401


def test_owner_can_create_update_and_archive_an_exercise(app: Flask) -> None:
    client = app.test_client()
    created = client.post("/api/v1/exercises", json=_write(), headers=_auth(app))

    assert created.status_code == 201
    exercise_id = created.get_json()["id"]
    updated_write = _write()
    updated_write["name"] = "Updated Custom Press"
    updated = client.patch(
        f"/api/v1/exercises/{exercise_id}", json=updated_write, headers=_auth(app)
    )
    archived = client.delete(f"/api/v1/exercises/{exercise_id}", headers=_auth(app))

    assert updated.status_code == 200
    assert updated.get_json()["name"] == "Updated Custom Press"
    assert archived.status_code == 204
    assert all(
        exercise["id"] != exercise_id for exercise in client.get("/api/v1/exercises").get_json()
    )
    assert any(
        exercise["id"] == exercise_id
        for exercise in client.get("/api/v1/exercises?include_archived=true").get_json()
    )


def test_write_and_query_validation_is_stable(app: Flask) -> None:
    client = app.test_client()
    unknown = _write("unknown_target_press")
    unknown["muscle_targets"][0]["slug"] = "not_a_muscle"  # type: ignore[index]

    assert client.get("/api/v1/exercises?unilateral=maybe").status_code == 400
    assert client.post("/api/v1/exercises", json={}, headers=_auth(app)).status_code == 400
    assert client.post("/api/v1/exercises", json=unknown, headers=_auth(app)).status_code == 400
    assert client.post("/api/v1/exercises", json=_write(), headers=_auth(app)).status_code == 201
    conflict = client.post("/api/v1/exercises", json=_write(), headers=_auth(app))
    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "SLUG_CONFLICT"
