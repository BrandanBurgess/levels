from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.features.today import repository as today_repository
from levels_api.models import Base, ScheduleState, User, UserRole, UserStatus, WorkoutTemplateItem
from levels_api.seed import seed_user_starter

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"
MONDAY = "2026-07-13"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'sessions-v2.db'}",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            users = [
                User(
                    email_normalized=f"journal-{index}@example.test",
                    password_hash="$argon2id$test-only",
                    status=UserStatus.ACTIVE,
                    role=UserRole.MEMBER,
                    token_version=0,
                    is_demo=False,
                )
                for index in (1, 2)
            ]
            session.add_all(users)
            session.flush()
            for index, user in enumerate(users, start=1):
                seed_user_starter(session, user, display_name=f"Journal {index}")
            application.config["USER_IDS"] = [user.id for user in users]
        with Session(engine) as session:
            application.config["TOKENS"] = [
                create_access_token(session.get(User, user_id))[0]
                for user_id in application.config["USER_IDS"]
            ]
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask, index: int = 0) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TOKENS'][index]}"}


def _today(app: Flask, index: int = 0) -> dict[str, object]:
    response = app.test_client().get(f"/api/v1/today?date={MONDAY}", headers=_auth(app, index))
    assert response.status_code == 200
    return response.get_json()


def _start(app: Flask, index: int = 0, key: str = "start-session-001") -> dict[str, object]:
    response = app.test_client().post(
        "/api/v1/sessions",
        headers={**_auth(app, index), "Idempotency-Key": key},
        json={"date": MONDAY, "expected_schedule_version": 0},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_all_session_routes_require_authentication(app: Flask) -> None:
    client = app.test_client()
    assert client.get("/api/v1/sessions").status_code == 401
    assert client.post("/api/v1/sessions", json={}).status_code == 401
    assert client.get("/api/v1/sessions/nope").status_code == 401
    assert client.post("/api/v1/sessions/nope/exercises", json={}).status_code == 401
    assert client.post("/api/v1/sessions/nope/complete").status_code == 401


def test_start_snapshots_effective_plan_and_replays_idempotently(app: Flask) -> None:
    client = app.test_client()
    today = _today(app)
    headers = {**_auth(app), "Idempotency-Key": "snapshot-start-001"}
    body = {"date": MONDAY, "expected_schedule_version": 0}
    first = client.post("/api/v1/sessions", headers=headers, json=body)
    replay = client.post("/api/v1/sessions", headers=headers, json=body)

    assert first.status_code == replay.status_code == 201
    started = first.get_json()
    assert replay.get_json()["id"] == started["id"]
    assert len(started["exercises"]) == len(today["exercise_plan"])
    assert started["exercises"][1]["planned_sets"] == 3
    assert started["exercises"][1]["rest_seconds"] == 150
    original_name = started["exercises"][1]["display_name"]
    source_id = started["exercises"][1]["source_template_item_id"]

    with app.app_context(), Session(get_engine()) as session, session.begin():
        template = session.get(WorkoutTemplateItem, source_id)
        template.sets = 9
        template.notes = "changed after start"
    unchanged = client.get(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).get_json()
    assert unchanged["exercises"][1]["display_name"] == original_name
    assert unchanged["exercises"][1]["planned_sets"] == 3
    assert unchanged["exercises"][1]["notes"] is None


def test_active_session_add_update_reorder_and_soft_remove(app: Flask) -> None:
    client = app.test_client()
    started = _start(app)
    add = client.post(
        f"/api/v1/sessions/{started['id']}/exercises",
        headers=_auth(app),
        json={
            "exercise_id": "plank",
            "expected_version": started["version"],
            "sequence": 0,
        },
    )
    assert add.status_code == 201
    item = add.get_json()
    current = client.get(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).get_json()
    assert current["version"] == 1
    assert current["exercises"][0]["id"] == item["id"]

    updated = client.patch(
        f"/api/v1/sessions/{started['id']}/exercises/{item['id']}",
        headers=_auth(app),
        json={"expected_version": 1, "planned_sets": 4, "notes": "Core finisher"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["version"] == 2
    assert updated.get_json()["exercises"][0]["planned_sets"] == 4

    active_ids = [row["id"] for row in updated.get_json()["exercises"] if row["removed_at"] is None]
    reordered_ids = list(reversed(active_ids))
    reordered = client.post(
        f"/api/v1/sessions/{started['id']}/exercises/reorder",
        headers=_auth(app),
        json={"expected_version": 2, "ordered_session_exercise_ids": reordered_ids},
    )
    assert reordered.status_code == 200
    assert [
        row["id"] for row in reordered.get_json()["exercises"] if row["removed_at"] is None
    ] == reordered_ids

    removed = client.delete(
        f"/api/v1/sessions/{started['id']}/exercises/{item['id']}?expected_version=3",
        headers=_auth(app),
    )
    assert removed.status_code == 200
    audit = next(row for row in removed.get_json()["exercises"] if row["id"] == item["id"])
    assert audit["removed_at"] is not None
    assert audit["removal_reason"] is not None


def test_logged_exercise_removal_requires_confirmation_and_keeps_history(app: Flask) -> None:
    client = app.test_client()
    started = _start(app)
    item = started["exercises"][1]
    logged = client.post(
        f"/api/v1/sessions/{started['id']}/sets",
        headers=_auth(app),
        json={
            "session_exercise_id": item["id"],
            "set_type": "working",
            "load_kg": 60,
            "reps": 8,
        },
    )
    assert logged.status_code == 201, logged.get_json()
    denied = client.delete(
        f"/api/v1/sessions/{started['id']}/exercises/{item['id']}?expected_version=0",
        headers=_auth(app),
    )
    assert denied.status_code == 409
    removed = client.delete(
        f"/api/v1/sessions/{started['id']}/exercises/{item['id']}?expected_version=0&confirm_logged_sets=true",
        headers=_auth(app),
    )
    assert removed.status_code == 200
    audit = next(row for row in removed.get_json()["exercises"] if row["id"] == item["id"])
    assert audit["removed_at"] is not None
    assert len(audit["sets"]) == 1


def test_completion_is_idempotent_and_completed_snapshot_is_immutable(app: Flask) -> None:
    client = app.test_client()
    started = _start(app)
    headers = {**_auth(app), "Idempotency-Key": "complete-session-001"}
    first = client.post(f"/api/v1/sessions/{started['id']}/complete", headers=headers)
    replay = client.post(f"/api/v1/sessions/{started['id']}/complete", headers=headers)
    assert first.status_code == replay.status_code == 200
    assert first.get_json()["completed_at"] == replay.get_json()["completed_at"]
    immutable = client.patch(
        f"/api/v1/sessions/{started['id']}/exercises/{started['exercises'][0]['id']}",
        headers=_auth(app),
        json={"expected_version": first.get_json()["version"], "planned_sets": 10},
    )
    assert immutable.status_code == 409


def test_completed_snapshot_survives_save_to_split_removals(app: Flask) -> None:
    client = app.test_client()
    started = _start(app)
    completed = client.post(
        f"/api/v1/sessions/{started['id']}/complete",
        headers={**_auth(app), "Idempotency-Key": "complete-history-001"},
    )
    assert completed.status_code == 200
    before = client.get(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).get_json()
    first = before["exercises"][0]

    saved = client.put(
        "/api/v1/today/exercises",
        headers={**_auth(app), "Idempotency-Key": "archive-template-history-001"},
        json={
            "local_date": MONDAY,
            "source_split_day_id": started["split_day_id"],
            "scope": "save_to_split",
            "expected_version": 0,
            "items": [
                {
                    "source_template_item_id": first["source_template_item_id"],
                    "exercise_id": first["exercise_id"],
                    "sequence": 0,
                    "item_type": first["item_type"],
                    "planned_sets": first["planned_sets"],
                    "rep_min": first["rep_min"],
                    "rep_max": first["rep_max"],
                    "rest_seconds": first["rest_seconds"],
                    "target_rir": first["target_rir"],
                    "optional": first["optional"],
                    "notes": first["notes"],
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.get_json()
    after = client.get(f"/api/v1/sessions/{started['id']}", headers=_auth(app)).get_json()
    assert after == before


def test_completion_cas_conflict_rolls_back_completion(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = _start(app)
    with app.app_context(), Session(get_engine()) as session, session.begin():
        state = session.get(ScheduleState, app.config["USER_IDS"][0])
        assert state is not None
        state.cursor_effective_date = date.fromisoformat(MONDAY)

    monkeypatch.setattr(today_repository, "update_schedule", lambda *args, **kwargs: None)
    response = app.test_client().post(
        f"/api/v1/sessions/{started['id']}/complete",
        headers={**_auth(app), "Idempotency-Key": "complete-conflict-001"},
    )
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "VERSION_CONFLICT"
    stored = app.test_client().get(f"/api/v1/sessions/{started['id']}", headers=_auth(app))
    assert stored.get_json()["status"] == "in_progress"
    assert stored.get_json()["completed_at"] is None


def test_cross_tenant_session_and_child_ids_are_hidden(app: Flask) -> None:
    foreign = _start(app, index=1, key="foreign-start-001")
    client = app.test_client()
    assert client.get(f"/api/v1/sessions/{foreign['id']}", headers=_auth(app)).status_code == 404
    assert (
        client.patch(
            f"/api/v1/sessions/{foreign['id']}",
            headers=_auth(app),
            json={"title": "stolen"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/sessions/{foreign['id']}/exercises",
            headers=_auth(app),
            json={"exercise_id": "plank", "expected_version": 0},
        ).status_code
        == 404
    )
    own = client.get("/api/v1/sessions", headers=_auth(app)).get_json()
    assert foreign["id"] not in {row["id"] for row in own}
    with app.app_context(), Session(get_engine()) as session:
        stored = session.scalar(select(User.id).where(User.id == app.config["USER_IDS"][1]))
        assert stored is not None
