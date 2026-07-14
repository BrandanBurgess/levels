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
            f"sqlite+pysqlite:///{tmp_path / 'sessions.db'}",
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


def _upper_day_id(app: Flask) -> str:
    return app.test_client().get("/api/v1/splits").get_json()[0]["days"][0]["id"]


def test_session_mutations_require_owner_authentication(app: Flask) -> None:
    client = app.test_client()
    assert client.post("/api/v1/sessions", json={"title": "Solo"}).status_code == 401
    assert client.patch("/api/v1/sessions/nope", json={"title": "Nope"}).status_code == 401
    assert client.delete("/api/v1/sessions/nope").status_code == 401


def test_start_from_template_snapshots_exercises_and_is_idempotent(app: Flask) -> None:
    client = app.test_client()
    headers = {**_auth(app), "Idempotency-Key": "start-upper-a-001"}
    payload = {"split_day_id": _upper_day_id(app), "date": "2026-07-13"}

    first = client.post("/api/v1/sessions", json=payload, headers=headers)
    repeated = client.post("/api/v1/sessions", json=payload, headers=headers)

    assert first.status_code == repeated.status_code == 201
    assert first.get_json()["id"] == repeated.get_json()["id"]
    assert first.get_json()["title"] == "Upper A — Incline + Back"
    assert first.get_json()["status"] == "in_progress"
    assert first.get_json()["exercises"][1]["display_name"] == "Incline Barbell Bench Press"


def test_complete_resume_and_public_summary_visibility(app: Flask) -> None:
    client = app.test_client()
    started = client.post(
        "/api/v1/sessions",
        json={"title": "Visible workout", "date": "2026-07-13"},
        headers=_auth(app),
    ).get_json()
    assert client.get(f"/api/v1/sessions/{started['id']}").status_code == 404

    completed = client.patch(
        f"/api/v1/sessions/{started['id']}",
        json={
            "status": "completed",
            "public_visibility": "summary",
            "perceived_effort": 8,
            "notes_private": "private detail",
            "notes_public": "public detail",
        },
        headers=_auth(app),
    )
    public = client.get(f"/api/v1/sessions/{started['id']}")

    assert completed.status_code == 200
    assert completed.get_json()["completed_at"] is not None
    assert public.status_code == 200
    assert public.get_json()["exercises"] == []
    assert "notes_private" not in public.get_json()
    assert "notes_public" not in public.get_json()

    resumed = client.patch(
        f"/api/v1/sessions/{started['id']}",
        json={"status": "in_progress"},
        headers=_auth(app),
    )
    assert resumed.get_json()["completed_at"] is None
    assert client.get(f"/api/v1/sessions/{started['id']}").status_code == 404


def test_list_filters_owner_and_public_sessions(app: Flask) -> None:
    client = app.test_client()
    session_id = client.post(
        "/api/v1/sessions",
        json={"split_day_id": _upper_day_id(app), "date": "2026-07-13"},
        headers=_auth(app),
    ).get_json()["id"]

    assert client.get("/api/v1/sessions").get_json() == []
    owner = client.get("/api/v1/sessions?public_only=false", headers=_auth(app)).get_json()
    assert [workout["id"] for workout in owner] == [session_id]
    filtered = client.get(
        "/api/v1/sessions?public_only=false&from=2026-07-14",
        headers=_auth(app),
    )
    assert filtered.get_json() == []
    by_exercise = client.get(
        "/api/v1/sessions?public_only=false&exercise_id=pull_up",
        headers=_auth(app),
    )
    assert [workout["id"] for workout in by_exercise.get_json()] == [session_id]


def test_delete_is_soft_and_validation_errors_are_stable(app: Flask) -> None:
    client = app.test_client()
    started = client.post(
        "/api/v1/sessions", json={"title": "Delete me"}, headers=_auth(app)
    ).get_json()
    assert client.delete(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).status_code == 204
    assert client.get(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).status_code == 404
    assert client.post("/api/v1/sessions", json={}, headers=_auth(app)).status_code == 400
    assert (
        client.post(
            "/api/v1/sessions",
            json={"title": "Bad key"},
            headers={**_auth(app), "Idempotency-Key": "short"},
        ).status_code
        == 400
    )
    assert client.get("/api/v1/sessions?from=invalid").status_code == 400
    assert client.get("/api/v1/sessions?public_only=perhaps").status_code == 400
