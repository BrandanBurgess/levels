from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from levels_api import Settings, create_app
from levels_api.auth.service import create_access_token
from levels_api.database import get_engine
from levels_api.models import Achievement, Base, PersonalRecord, RecordType
from levels_api.seed import seed_session

JWT_SECRET = "tests-only-jwt-signing-key-32-characters-long"


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Flask]:
    application = create_app(
        Settings.for_testing(
            f"sqlite+pysqlite:///{tmp_path / 'records.db'}",
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


def _session_exercise(
    app: Flask, exercise_id: str = "incline_barbell_bench_press"
) -> tuple[str, str]:
    client = app.test_client()
    workout = client.post(
        "/api/v1/sessions", json={"title": "Record test"}, headers=_auth(app)
    ).get_json()
    item = client.post(
        f"/api/v1/sessions/{workout['id']}/exercises",
        json={"exercise_id": exercise_id},
        headers=_auth(app),
    ).get_json()
    return workout["id"], item["id"]


def _load_reps(
    item_id: str, load: float, reps: int, set_type: str = "working"
) -> dict[str, object]:
    return {
        "session_exercise_id": item_id,
        "set_type": set_type,
        "load_kg": load,
        "reps": reps,
        "rir": 2,
        "form_quality": 4,
        "pain_flag": False,
    }


def test_qualifying_set_creates_records_once_and_idempotently(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app)
    headers = {**_auth(app), "Idempotency-Key": "record-set-0001"}
    write = _load_reps(item_id, 60, 10)

    first = client.post(f"/api/v1/sessions/{workout_id}/sets", json=write, headers=headers)
    repeated = client.post(f"/api/v1/sessions/{workout_id}/sets", json=write, headers=headers)

    assert first.status_code == repeated.status_code == 201
    assert {item["record_type"] for item in first.get_json()["affected_records"]} == {
        "max_load",
        "reps_at_load",
        "estimated_1rm",
    }
    assert len(first.get_json()["new_achievements"]) == 3
    assert repeated.get_json()["new_achievements"] == []
    assert "No max attempt is needed" in next(
        item["message"]
        for item in first.get_json()["new_achievements"]
        if item["title"] == "New estimated 1RM"
    )

    with app.app_context(), Session(get_engine()) as session:
        assert session.scalar(select(func.count(Achievement.id))) == 3
        assert session.scalar(select(func.count(PersonalRecord.id))) == 3


def test_warmup_sets_do_not_create_records(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app)
    response = client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json=_load_reps(item_id, 100, 10, "warmup"),
        headers=_auth(app),
    )
    assert response.status_code == 201
    assert response.get_json()["new_achievements"] == []
    assert response.get_json()["affected_records"] == []


def test_only_strict_improvements_create_new_achievements(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app)
    client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json=_load_reps(item_id, 60, 10),
        headers=_auth(app),
    )
    second = client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json=_load_reps(item_id, 65, 5),
        headers=_auth(app),
    )
    assert [item["title"] for item in second.get_json()["new_achievements"]] == ["New max load"]


def test_historical_edit_and_delete_rebuild_current_records(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app)
    first = client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json=_load_reps(item_id, 60, 10),
        headers=_auth(app),
    ).get_json()["set"]
    second = client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json=_load_reps(item_id, 65, 5),
        headers=_auth(app),
    ).get_json()["set"]

    edited = client.patch(
        f"/api/v1/sets/{second['id']}",
        json={**_load_reps(item_id, 55, 12), "sequence": 2},
        headers=_auth(app),
    )
    records = {item["record_type"]: item for item in edited.get_json()["affected_records"]}
    assert records["max_load"]["value_numeric"] == 60
    assert records["reps_at_load"]["value_numeric"] == 12
    assert edited.get_json()["new_achievements"][0]["title"] == "New rep record"

    assert client.delete(f"/api/v1/sets/{second['id']}", headers=_auth(app)).status_code == 204
    with app.app_context(), Session(get_engine()) as session:
        reps_record = session.scalar(
            select(PersonalRecord).where(
                PersonalRecord.record_type == RecordType.REPS_AT_LOAD,
                PersonalRecord.is_current.is_(True),
            )
        )
        assert reps_record is not None
        assert reps_record.value_numeric == 10
        assert reps_record.set_log_id == first["id"]


def test_completion_adds_session_volume_once(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app)
    for load, reps in [(60, 10), (65, 5)]:
        client.post(
            f"/api/v1/sessions/{workout_id}/sets",
            json=_load_reps(item_id, load, reps),
            headers=_auth(app),
        )

    assert (
        client.post(f"/api/v1/sessions/{workout_id}/complete", headers=_auth(app)).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/sessions/{workout_id}/complete", headers=_auth(app)).status_code
        == 200
    )
    with app.app_context(), Session(get_engine()) as session:
        volume = session.scalar(
            select(PersonalRecord).where(
                PersonalRecord.record_type == RecordType.SESSION_VOLUME,
                PersonalRecord.is_current.is_(True),
            )
        )
        assert volume is not None
        assert volume.value_numeric == 925
        count = session.scalar(
            select(func.count(Achievement.id)).where(
                Achievement.idempotency_key.like("record:%:session_volume")
            )
        )
        assert count == 1


def test_conditioning_measurements_create_supported_records(app: Flask) -> None:
    client = app.test_client()
    workout_id, item_id = _session_exercise(app, "plank")
    response = client.post(
        f"/api/v1/sessions/{workout_id}/sets",
        json={
            "session_exercise_id": item_id,
            "set_type": "working",
            "duration_seconds": 75,
            "pain_flag": False,
        },
        headers=_auth(app),
    )
    assert [item["record_type"] for item in response.get_json()["affected_records"]] == ["duration"]
