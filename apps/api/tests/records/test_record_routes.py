from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Base, ScheduleState, User, VisibilitySettings
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'record-routes.db'}",
            admin_username="brandan",
            admin_password_hash="$argon2id$unused-in-route-tests",
            jwt_secret_key=JWT_SECRET,
        )
    )
    with application.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            seeded = seed_session(session)
            user = session.get(User, seeded.user_id)
            assert user is not None
            token, _ = create_access_token(user)
            application.config["TEST_USER_ID"] = user.id
        application.config["TEST_ACCESS_TOKEN"] = token
    yield application
    with application.app_context():
        get_engine().dispose()


def _auth(app: Flask) -> dict[str, str]:
    return {"Authorization": f"Bearer {app.config['TEST_ACCESS_TOKEN']}"}


def _create_record(
    app: Flask,
    *,
    exercise_id: str = "incline_barbell_bench_press",
    visibility: str = "full",
    load: int = 60,
) -> None:
    client = app.test_client()
    with app.app_context(), Session(get_engine()) as db:
        schedule = db.get(ScheduleState, str(app.config["TEST_USER_ID"]))
        assert schedule is not None
        expected_schedule_version = schedule.version
    workout = client.post(
        "/api/v1/sessions",
        json={
            "title": "Record history",
            "expected_schedule_version": expected_schedule_version,
        },
        headers={**_auth(app), "Idempotency-Key": f"record-history-{load}"},
    ).get_json()
    item = client.post(
        f"/api/v1/sessions/{workout['id']}/exercises",
        json={"exercise_id": exercise_id, "expected_version": workout["version"]},
        headers=_auth(app),
    ).get_json()
    client.post(
        f"/api/v1/sessions/{workout['id']}/sets",
        json={
            "session_exercise_id": item["id"],
            "set_type": "working",
            "load_kg": load,
            "reps": 8,
            "pain_flag": False,
        },
        headers=_auth(app),
    )
    client.post(
        f"/api/v1/sessions/{workout['id']}/complete",
        headers={**_auth(app), "Idempotency-Key": f"record-complete-{load}"},
    )


def test_records_are_named_filtered_and_current_by_default(app: Flask) -> None:
    _create_record(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/records?exercise_id=incline_barbell_bench_press", headers=_auth(app)
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert {item["record_type"] for item in payload} == {
        "max_load",
        "reps_at_load",
        "estimated_1rm",
        "session_volume",
    }
    assert {item["exercise_name"] for item in payload} == {"Incline Barbell Bench Press"}
    assert client.get("/api/v1/records?exercise_id=plank", headers=_auth(app)).get_json() == []


def test_record_history_and_boolean_validation(app: Flask) -> None:
    _create_record(app, load=60)
    _create_record(app, load=70)
    client = app.test_client()

    current = client.get("/api/v1/records", headers=_auth(app)).get_json()
    history = client.get("/api/v1/records?current_only=false", headers=_auth(app)).get_json()

    assert len(history) > len(current)
    assert any(item["value_numeric"] == 60 for item in history)
    invalid = client.get("/api/v1/records?current_only=sometimes", headers=_auth(app))
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_records_require_authentication(app: Flask) -> None:
    _create_record(app, visibility="private")
    client = app.test_client()

    assert client.get("/api/v1/records").status_code == 401
    assert client.get("/api/v1/records", headers=_auth(app)).get_json()


def test_profile_visibility_does_not_hide_own_records(app: Flask) -> None:
    _create_record(app, visibility="full")
    client = app.test_client()

    with app.app_context(), Session(get_engine()) as session, session.begin():
        visibility = session.scalar(select(VisibilitySettings))
        assert visibility is not None
        visibility.show_personal_records = False
    assert client.get("/api/v1/records", headers=_auth(app)).get_json()
    assert client.get("/api/v1/records?current_only=false", headers=_auth(app)).get_json()

    with app.app_context(), Session(get_engine()) as session, session.begin():
        visibility = session.scalar(select(VisibilitySettings))
        assert visibility is not None
        visibility.show_progress_charts = False
    assert client.get("/api/v1/records?current_only=false", headers=_auth(app)).get_json()


def test_in_progress_records_are_owner_only(app: Flask) -> None:
    client = app.test_client()
    workout = client.post(
        "/api/v1/sessions",
        json={"title": "Active record", "expected_schedule_version": 0},
        headers={**_auth(app), "Idempotency-Key": "active-record-session"},
    ).get_json()
    item = client.post(
        f"/api/v1/sessions/{workout['id']}/exercises",
        json={
            "exercise_id": "incline_barbell_bench_press",
            "expected_version": workout["version"],
        },
        headers=_auth(app),
    ).get_json()
    client.post(
        f"/api/v1/sessions/{workout['id']}/sets",
        json={
            "session_exercise_id": item["id"],
            "set_type": "working",
            "load_kg": 80,
            "reps": 5,
            "pain_flag": False,
        },
        headers=_auth(app),
    )

    assert client.get("/api/v1/records", headers=_auth(app)).get_json()
